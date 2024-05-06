#!/bin/bash

# Change the current working directory to the script's directory
cd "$(dirname "$0")"

# Check if conda is installed
if ! command -v conda &> /dev/null
then
    echo -e "\033[1;33mConda is not installed. Installing Miniforge...\033[0m"

    # Determine the architecture of the machine
    ARCHITECTURE=$(uname -m)

    if [[ "$ARCHITECTURE" == "arm64" ]]; then
        # Download Miniforge installer for Apple Silicon
        curl -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-arm64.sh
        # Install Miniforge
        bash Miniforge3-MacOSX-arm64.sh -b
    else
        # Download Miniforge installer for Intel Mac
        curl -O https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-MacOSX-x86_64.sh
        # Install Miniforge
        bash Miniforge3-MacOSX-x86_64.sh -b
    fi
else
    echo -e "\033[1;33mConda is already installed.\033[0m"
fi

# Determine the shell of the user
SHELLTYPE=$(basename "$SHELL")

# Initialize conda
if [[ "$SHELLTYPE" == "bash" ]]; then
    eval "$(/Users/$USER/miniforge3/bin/conda shell.bash hook)"
elif [[ "$SHELLTYPE" == "zsh" ]]; then
    eval "$(/Users/$USER/miniforge3/bin/conda shell.zsh hook)"
fi

# Create a new conda environment with Python, if it doesn't exist
if ! conda env list | grep -q 'venv-appagent'
then
    echo -e "\033[1;33mCreating a new conda environment 'venv-appagent'...\033[0m"
    conda create -n venv-appagent python=3.9 -y
else
    echo -e "\033[1;33mConda environment 'venv-appagent' already exists.\033[0m"
fi

# Activate the conda environment
echo -e "\033[1;33mActivating the conda environment 'venv-appagent'...\033[0m"
conda activate venv-appagent

# Upgrade pip
echo -e "\033[1;33mUpgrading pip...\033[0m"
python -m pip install -U pip

# Install dependencies
echo -e "\033[1;33mInstalling dependencies...\033[0m"
pip install -r requirements.txt

# Verify installation
echo -e "\033[1;33mVerifying installation...\033[0m"
python -c "
try:
    import tkinter
    print('\033[1;32mInstallation successful.\033[0m')
except ImportError:
    print('\033[1;31mInstallation failed.\033[0m')
"