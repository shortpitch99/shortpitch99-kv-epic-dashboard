#!/bin/bash
# KV Epic Dashboard Runner

set -e
cd "$(dirname "$0")"

echo "🔧 Setting up virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✓ Virtual environment created"
fi

echo "📦 Installing dependencies..."
source .venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1
echo "✓ Dependencies installed"

if [ ! -d "data/weekly_reports" ]; then
    echo "⚠️ No weekly reports found yet."
    echo "   Run ./run_report.sh first, then launch the dashboard."
fi

echo "📊 Starting KV Epic Dashboard..."
echo "🌐 Dashboard will open in your browser at http://localhost:8501"
echo "🔄 Press Ctrl+C to stop the dashboard"
echo ""

streamlit run app.py
