Write-Host "Setting up the Python environment..."
python -m venv .venv

Write-Host "Activating the virtual environment..."
. ./.venv/Scripts/Activate.ps1

echo "Installing required packages..."
python -m pip install --upgrade pip
pip install -r requirements.txt

if (-not (Get-Command "ollama" -ErrorAction SilentlyContinue)) {
    Write-Error "Ollama not found. Install from https://ollama.com/download."
    exit 1
}

Write-Host "Pulling and Creating Ollama models..."
ollama pull HammerAI/mistral-nemo-uncensored:latest   # Foundation model for personas
ollama create dem-model -f model_files/democrat_v3.2.mf
ollama create rep-model -f model_files/republican_v3.2.mf