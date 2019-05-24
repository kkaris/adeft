# Deft

Deft (Disambiguation of Entities From Text-context)
is a utility for building models to disambiguate acronyms and other abbreviations of biological terms in the scientific literature. It makes use of an implementation of the [Acromine](http://www.chokkan.org/research/acromine/) algorithm developed
by the [NaCTeM](http://www.nactem.ac.uk/index.php) at the University of Manchester
to identify possible longform expansions for shortforms in a text corpus.
It allows users to build disambiguation models to disambiguate shortforms based
on their text context. A growing number of pretrained disambiguation models are publically available to download through Deft.
## Installation

Deft works with Python versions 3.5 and above. To install, point pip to the
source repository at

    $ pip install git+https://github.com/indralab/deft.git

Deft's pretrained machine learning models can then be downloaded with the command

    $ python -m deft.download

## Using Deft
A dictionary of available models can be imported with `from deft import available_models`

The dictionary maps shortforms to model names. It's possible for multiple equivalent
shortforms to map to the same model

Here's an example of running a disambiguator for ER on a list of texts

```python
from deft.disambiguate import load_disambiguator

er_dd = load_disambiguator('ER')

    ...

er_dd.disambiguate(texts)
```

Users may also build and train their own disambiguators. See the documention
for more info.


## Documentation

Documentation is available at
[https://deft.readthedocs.io](http://deft.readthedocs.io)
    

