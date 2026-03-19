#!/bin/bash

# Project RepoHunter: Parallel Cloud Orchestrator
# This script launches the RepoHunter factory in high-speed parallel mode.

echo "🌍 HYPER-SCALE CLOUD-PARALLEL LAUNCH..."

# 1. Ensure Dependencies
if [ ! -f "venv/bin/activate" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt || pip install requests pyyaml tqdm mlx-lm python-dotenv

# 2. Configure Environment
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "📝 Creating .env from example..."
        cp .env.example .env
        echo "⚠️  WARNING: Please edit .env and update your API keys (Groq/GitHub)!"
    else
        echo "❌ .env.example missing. Cannot proceed."
        exit 1
    fi
fi

# 3. Choose Launch Mode
echo "--------------------------------"
echo "Select Launch Mode:"
echo "1) 🔍 Universal Ocean Hunter (Background)"
echo "2) 🧠 Parallel AI Synthesizer (High Speed)"
echo "3) 🚀 Full Parallel Factory (Both)"
echo "--------------------------------"
read -p "Enter choice [1-3]: " choice

case $choice in
    1)
        echo "🔍 Launching Ocean Hunter..."
        nohup python -u github_repohunter/global_hunter.py >> ocean_scan.log 2>&1 &
        ;;
    2)
        echo "🧠 Launching Parallel Synthesizer..."
        python github_repohunter/ai_dataset_synthesizer_parallel.py
        ;;
    3)
        echo "🚀 Launching Full Parallel Factory..."
        nohup python -u github_repohunter/global_hunter.py >> ocean_scan.log 2>&1 &
        python github_repohunter/ai_dataset_synthesizer_parallel.py
        ;;
    *)
        echo "❌ Invalid choice."
        ;;
esac

echo "✅ Launch sequence complete. Monitor logs for details."
