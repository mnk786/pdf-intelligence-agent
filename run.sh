#!/bin/bash
# Start script for the PDF Intelligence Agent
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_CONFIG_DIR="$DIR/.streamlit"

if [ ! -d ".venv" ]; then
    echo "Virtual environment not found. Setting up..."
    python3 -m venv .venv
    .venv/bin/pip install -r requirements.txt
fi

echo "Starting PDF Intelligence Agent..."
.venv/bin/streamlit run app.py
