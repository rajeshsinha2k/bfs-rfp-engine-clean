#!/bin/zsh
export VIRTUAL_ENV="$(pwd)/backend/.venv"
export PATH="$VIRTUAL_ENV/bin:$PATH"
unset PYTHONHOME
