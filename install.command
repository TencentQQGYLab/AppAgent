#!/bin/zsh

# Create a virtual environment
python3 -m venv ~/venv-appagent

# Activate the virtual environment
source ~/venv-appagent/bin/activate

# Upgrade pip
python -m pip install -U pip

# Install dependencies
pip install -r requirements.txt

# Verify installation
python -c "
try:
    import tkinter
    print('Installation successful.')
except ImportError:
    print('Installation failed.')
"