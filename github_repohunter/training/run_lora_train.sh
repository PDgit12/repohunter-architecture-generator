#!/bin/bash

# Project RepoHunter: LoRA Training Orchestrator
# This script triggers the MLX fine-tuning process.

echo "🚀 Starting Project RepoHunter LoRA Fine-Tuning..."
echo "📍 Data Directory: github_repohunter/training/data"
echo "⚙️ Config File: github_repohunter/training/mlx_train_config.yaml"

# Activate virtual environment
source venv/bin/activate

# Start training
# Note: This will automatically download the base model if not found locally (~5GB)
mlx_lm.lora --config github_repohunter/training/mlx_train_config.yaml
