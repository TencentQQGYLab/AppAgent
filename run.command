#!/bin/zsh

# Initialize conda
eval "$(/Users/$USER/miniforge3/bin/conda shell.bash hook)"

# Activate the conda environment
conda activate venv-appagent

# Change the current working directory to the script's directory
cd "$(dirname "$0")"

# Run the application
python learn_gui.py