#!/usr/bin/env bash
set -e

echo "Setting up Python environment..."
python -m venv .venv

source .venv/bin/activate

echo "Installing required packages..."
python -m pip install --upgrade pip
pip install -r requirements.txt

if ! command -v ollama >/dev/null 2>&1; then
    echo "Ollama not found. Install from https://ollama.com/download."
    exit 1
fi

echo "Pulling and Creating Ollama models..."
ollama pull HammerAI/mistral-nemo-uncensored:latest # Foundation model for personas
ollama create dem-model -f model_files/democrat_v3.2.mf
ollama create rep-model -f model_files/republican_v3.2.mf