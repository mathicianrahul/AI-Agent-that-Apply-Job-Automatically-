#!/usr/bin/env bash
set -e

echo "==================================================="
echo "       JobPilot AI - One-Click Launcher"
echo "==================================================="

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] python3 could not be found. Please install Python 3.11+."
    exit 1
fi

# 2. Virtual environment
if [ ! -d "venv" ]; then
    echo "[INFO] Creating Python virtual environment (venv)..."
    python3 -m venv venv
fi

# 3. Activate venv
source venv/bin/activate

# 4. Check .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "[INFO] Creating .env from .env.example..."
        cp .env.example .env
    fi
fi

# 5. Install dependencies
echo "[INFO] Checking dependencies in requirements.txt..."
pip install -r requirements.txt --quiet

# 6. Launch Streamlit
echo "==================================================="
echo "[SUCCESS] Starting JobPilot AI Dashboard..."
echo "Open your browser to http://localhost:8501"
echo "==================================================="
streamlit run app.py
