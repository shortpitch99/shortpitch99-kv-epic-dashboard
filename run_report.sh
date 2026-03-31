#!/bin/bash
# KV Weekly Report Generator

set -e

echo "🚀 Starting KV weekly report generation..."

if [ ! -d ".venv" ]; then
    echo "🔧 Creating virtual environment..."
    python3 -m venv .venv
fi

echo "📦 Installing dependencies..."
source .venv/bin/activate
pip install -r requirements.txt > /dev/null 2>&1

if [ -f ".env" ]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
    echo "✓ Loaded KV .env"
fi

# Load LLM vars from QC .env if missing locally
if [ -z "${LLM_GW_EXPRESS_KEY:-}" ] || [ -z "${OPENAI_USER_ID:-}" ]; then
    if [ -f "/Users/rchowdhuri/QC/.env" ]; then
        set -a
        # shellcheck disable=SC1091
        source /Users/rchowdhuri/QC/.env
        set +a
        echo "✓ Loaded LLM defaults from QC .env"
    fi
fi

if [ -z "${SF_INSTANCE_URL:-}" ] || [ -z "${SF_ACCESS_TOKEN:-}" ]; then
    if [ -f "/Users/rchowdhuri/QC/.env" ]; then
        set -a
        # shellcheck disable=SC1091
        source /Users/rchowdhuri/QC/.env
        set +a
        echo "✓ Loaded SF credentials from QC .env"
    fi
fi

echo "🤖 Generating weekly report narrative and metadata..."
python3 run_report.py "$@"

echo ""
echo "✅ Weekly report generated."
echo "🌐 Launch dashboard with: ./run_dashboard.sh"
