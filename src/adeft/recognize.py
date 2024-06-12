"""Implements the disambiguation of shortforms based on recognizing an
explicit defining pattern in text."""

import re
import string
import logging


from adeft.nlp import stem, word_tokenize, word_detokenize
from adeft.util import get_candidate_fragments, get_candidate, SearchTrie

logger = logging.getLogger(__file__)

try:
    from adeft.score import AlignmentBasedScorer
except Exception:
    logger.info('OneShotRecognizer not available. Extension module for'
                ' AlignmentBasedScorer is missing')


class BaseRecognizer(object):
    """Base class for recognizers

    Recognizers are built to identify longform expansions for a shortform by
    searching for defining patterns (DPs).

    Parameters
    ----------
    shortform : str
        shortform to be recognized
    window : Optional[int]
        Specifies range of characters before a defining pattern (DP)
        to consider when finding longforms. Should be set to the same value
        that was used in the AdeftMiner that was used to find longforms.
        Default: 100
    """
    def __init__(self, shortform, window=100):
        self.shortform = shortform
        self.window = window

    def recognize(self, text):
        """Find longforms in text by searching for defining patterns (DPs)

        Parameters
        ----------
        text : str
            Sentence where we seek to disambiguate shortform

        Returns
        -------
        expansions : set of str
            Set of longforms corresponding to shortform in sentence if a
            defining pattern is matched. Returns None if no defining patterns
            are found
        """
        results = []
        fragments = get_candidate_fragments(text, self.shortform,
                                            window=self.window)
        for fragment in fragments:
            if not fragment:
                continue
            tokens, longform_map = get_candidate(fragment)
            # search for longform in trie
            result = self._search(tokens)
            # if a longform is recognized, add it to output list
            if result:
                longform = result['longform']
                num_tokens = len(word_tokenize(longform))
                longform_text = longform_map[num_tokens]
                result = self._post_process(result)
                result['longform_text'] = longform_text
                results.append((result))
        return results

    def strip_defining_patterns(self, text):
        """Return text with defining patterns stripped

       This is useful for training machine learning models where training
       labels are generated by finding defining patterns (DP)s. Models must
       be trained to disambiguate texts that do not contain a defining
       pattern.

       The output on the first sentence of the previous paragraph is
       "This is useful for training machine learning models where training
       labels are generated by finding DPs."

       Parameters
       ----------
       text : str
           Text to remove defining patterns from

       Returns
       -------
       stripped_text : str
           Text with defining patterns replaced with shortform
        """
        fragments = get_candidate_fragments(text, self.shortform)
        for fragment in fragments:
            # Each fragment is tokenized and its longform is identified
            tokens = word_tokenize(fragment)
            result = self._search([token for token, _ in tokens
                                   if token not in string.punctuation])
            if result is None:
                # For now, ignore a fragment if its grounding has no longform
                # from the grounding map
                continue
            longform = result['longform']
            # Remove the longform from the fragment, keeping in mind that
            # punctuation is ignored when extracting longforms from text
            num_words = len(longform.split())
            i = 0
            j = len(tokens) - 1
            while i < num_words:
                if re.match(r'\w+', tokens[j][0]):
                    i += 1
                j -= 1
                if i > self.window:
                    break
            text = text.replace(fragment.strip(),
                                word_detokenize(tokens[:j+1]))
        # replace all instances of parenthesized shortform with shortform
        stripped_text = re.sub(r'\(\s*%s\s*\)'
                               % self.shortform,
                               ' ' + self.shortform + ' ', text)
        stripped_text = ' '.join(stripped_text.split())
        return stripped_text

    def _search(self, tokens):
        """Method to identify longform expansion from tokens preceeding DP

        This method should take a list of tokens preceeding a defining pattern
        and return a longform expansion as a single string
        """
        raise NotImplementedError

    def _post_process(self, text):
        """Post-processing step for longform expansion

        Default to no post-processing
        """
        return text


class AdeftRecognizer(BaseRecognizer):
    """Class for recognizing longforms by searching for defining patterns (DP)

    Searches text for the pattern "<longform> (<shortform>)" for a collection
    of grounded longforms supplied by the user.

    Parameters
    ----------
    shortform : str
        shortform to be recognized
    grounding_map : dict[str, str]
        Dictionary mapping longform texts to their groundings
    window : Optional[int]
        Specifies range of characters before a defining pattern (DP)
        to consider when finding longforms. Should be set to the same value
        that was used in the AdeftMiner that was used to find longforms.
        Default: 100

    Attributes
    ----------
    _trie : :py:class:`adeft.recognize._TrieNode`
        Trie used to search for longforms. Edges correspond to stemmed tokens
        from longforms. They appear in reverse order to the bottom of the trie
        with terminal nodes containing the associated longform in their data.
    """
    def __init__(self, shortform, grounding_map, window=100):
        self.grounding_map = grounding_map
        self.search_trie = SearchTrie(grounding_map,
                                      token_map=lambda x: stem(x).lower())
        super().__init__(shortform, window)

    def _search(self, tokens):
        res, _ = self.search_trie.search(tokens)
        if res is not None:
            res = {'longform': res}
        return res

    def _post_process(self, result):
        """Map longform to associated grounding in grounding map"""
        return {'grounding': self.grounding_map[result['longform']]}


class OneShotRecognizer(BaseRecognizer):
    """Identify longform expansions using subsequence matching

    Uses a string matching algorithm to determine longform boundaries
    for a defining pattern for only a single text.

    Attributes
    ----------
    shortform : str
        shortform to be recognized
    window : Optional[int]
        Specifies range of characters before a defining pattern (DP)
        to consider when finding longforms. Should be set to the same value
        that was used in the AdeftMiner that was used to find longforms.
        Default: 100
    **params
        Parameters for :py:class`adeft.score.AdeftLongformScorer`
    """
    def __init__(self, shortform, window=100, **params):
        try:
            self.scorer = AlignmentBasedScorer(shortform, **params)
        except NameError:
            logger.exception('OneShotRecognizer not available.'
                             ' Extension module for AlignmentBasedScorer'
                             ' is missing')
        super().__init__(shortform, window)

    def _search(self, tokens):
        """Use AdeftLongformScorer to identify expansions"""
        scores = self.scorer.expanding_score([stem(token).lower()
                                              for token in tokens])
        n = len(tokens)
        i = max(range(len(scores)), key=lambda i: scores[i])
        longform = ' '.join(tokens[n-i-1:])
        return {'longform': longform, 'score': scores[i]}

    def _post_process(self, result):
        return {'score': result['score']}