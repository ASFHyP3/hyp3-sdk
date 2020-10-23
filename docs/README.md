# HyP3 SDK documentation

HyP3 SDK documentation is built using [MkDocs](https://www.mkdocs.org/) and the
[Material theme](https://squidfunk.github.io/mkdocs-material/). 

## How to

### Setting up a development environment

From the repository root, you can set up a conda environment with all the 
necessary dependencies for development of the SDK

```
conda env create -f conda-env.yml
conda activate hyp3-sdk
python -m pip install -e ".[develop]"
```

### Build and view the documentation site
```
mkdocs serve
```

which will allow you to view the documentation at http://127.0.0.1:8000/. This
make target will automatically watch for new/changed files in this directory and
rebuild the website so you can see your changes live (just refresh the webpage!).

*Note: Because this captures your terminal (`crtl+c` to exit), it's recommended you
run this in its own terminal.*

### Deploy

Currently, the SDK documentation is **not deployed** on its own. It is built as
a single page website and consumed when the general HyP3 documentation is built:
<https://asfhyp3.github.io/using/sdk/>
The MkDocs structure here mirrors the HyP3 documentation and is only intended for
developers to be able to easily view the rendered SDK documentation.
