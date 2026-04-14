#!/bin/bash
# KV Weekly Report Generator

set -e
cd "$(dirname "$0")"

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

# LLM keys: only KV/.env or your shell — never taken from QC (even when SF loads from QC).
_kv_llm_key="${LLM_GW_EXPRESS_KEY:-}"
_kv_openai_user="${OPENAI_USER_ID:-}"

if [ -z "${SF_INSTANCE_URL:-}" ] || [ -z "${SF_ACCESS_TOKEN:-}" ]; then
    if [ -f "/Users/rchowdhuri/QC/.env" ]; then
        set -a
        # shellcheck disable=SC1091
        source /Users/rchowdhuri/QC/.env
        set +a
        echo "✓ Loaded SF credentials from QC .env"
    fi
fi

if [ -n "${_kv_llm_key}" ]; then
    export LLM_GW_EXPRESS_KEY="${_kv_llm_key}"
else
    unset LLM_GW_EXPRESS_KEY
fi
if [ -n "${_kv_openai_user}" ]; then
    export OPENAI_USER_ID="${_kv_openai_user}"
else
    unset OPENAI_USER_ID
fi
unset _kv_llm_key _kv_openai_user

echo "🤖 Generating weekly report narrative and metadata..."
python3 run_report.py "$@"

echo ""
echo "✅ Weekly report generated."
echo "   Local dashboard reads: data/weekly_reports/  (and falls back to cloud_reports/)"
echo "   Streamlit Cloud uses: cloud_reports/ in the Git repo — commit and push to deploy."
echo "🌐 Launch dashboard with: ./run_dashboard.sh"
