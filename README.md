## Context Builder
Build context of codebases for AI injection

Currently python is supported. This may change in the future 


### Getting Started

```bash
uv venv --python 3.13 
uv sync

source .venv/bin/activate

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
  --pip-args="git+https://github.com/HarrisDePerceptron/context_builder.git"

```

### Usage

```bash
context_builder <source directory> --out <output file>
content_builder <source directory> --out <output file> --include-source

```
### Context Layout 
```
1. Project structure (ASCII tree)
2. Function signatures
3. Class definitions  ← now lists attribute *types*
4. Dependencies
5. Combined source code  (only when --include-source is given)
```

