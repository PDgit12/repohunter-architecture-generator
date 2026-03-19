#!/bin/bash

# Configuration
BASE_MODEL="mlx-community/Meta-Llama-3-8B-Instruct-4bit"
DATA_DIR="github_repohunter/training/data"
ADAPTER_PATH="github_repohunter/training/adapters"
ITERATIONS=600  # Start with 600 iterations for initial refinement
BATCH_SIZE=1 
LEARNING_RATE=1e-5

echo "🚀 Starting RepoHunter MLX Fine-Tuning..."
echo "📍 Data Directory: $DATA_DIR"
echo "📍 Base Model: $BASE_MODEL"

# Execute LoRA Training
/Users/piyushdua/Desktop/instabot/venv/bin/python3 -m mlx_lm.lora \
    --model "$BASE_MODEL" \
    --train \
    --data "$DATA_DIR" \
    --iters "$ITERATIONS" \
    --batch-size "$BATCH_SIZE" \
    --learning-rate "$LEARNING_RATE" \
    --adapter-path "$ADAPTER_PATH" \
    --save-every 100

echo "✅ Fine-Tuning Complete! Adapter saved to $ADAPTER_PATH"
