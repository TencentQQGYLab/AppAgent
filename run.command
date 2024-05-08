#!/bin/zsh

# Check if conda is initialized
if [[ -z "$CONDA_EXE" ]]; then
    # Initialize conda
    echo -e "\033[1;33mInitializing conda...\033[0m"
    eval "$(/Users/$USER/miniforge3/bin/conda shell.bash hook)"
else
    echo -e "\033[1;33mConda is already initialized.\033[0m"
fi

# Check if the conda environment 'venv-appagent' is activated
if [[ "$CONDA_DEFAULT_ENV" != "venv-appagent" ]]; then
    # Activate the conda environment
    echo -e "\033[1;33mActivating the conda environment 'venv-appagent'...\033[0m"
    source activate venv-appagent 
else
    echo -e "\033[1;33mConda environment 'venv-appagent' is already activated.\033[0m"
fi

# Change the current working directory to the script's directory
cd "$(dirname "$0")"

# Run the application
python learn_gui.py