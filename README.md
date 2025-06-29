## Context Builder 

### Getting Started

```bash
uv venv --python 3.13 
uv sync

source .venv/bin/activate

python main.py <source directory> --out <output file>
python main.py <source directory> --out <output file> --include-source
```

### Installing 

```bash
brew install pipx          # Pipx using any platform specific
pipx ensurepath            # ensures ~/.local/bin is on PATH
pipx install .             # inside project folder
```

Or
```bash

pipx install context_builder \
  --pip-args="git+https://github.com/HarrisDePerceptron/context_builder.git@v0.1.0#egg=context_builder"

```
```
