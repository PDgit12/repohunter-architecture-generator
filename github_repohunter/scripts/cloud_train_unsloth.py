"""
RepoHunter Cloud Training — Unsloth + SFTTrainer
Runs on Lightning AI GPU (T4/A10/A100).

CRITICAL: Uses Llama-3 chat template for training data — matches inference prompt format exactly.
"""
import os
import sys
import json
import time
import subprocess
import importlib

# ─── Auto-Dependency Setup ───────────────────────────────────────────────────
def setup_dependencies():
    required = {
        "unsloth": "unsloth",
        "trl": "trl",
        "transformers": "transformers",
        "datasets": "datasets",
        "torch": "torch",
    }
    for pkg, import_name in required.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            print(f"📦 Installing {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

setup_dependencies()

from unsloth import FastLanguageModel
import torch
from trl import SFTTrainer
from transformers import TrainingArguments
from datasets import Dataset, load_dataset

# ─── Config ───────────────────────────────────────────────────────────────────
MODEL_NAME = os.getenv("MODEL_NAME", "unsloth/llama-3-8b-instruct-bnb-4bit")
MAX_SEQ_LENGTH = 2048
OUTPUT_DIR = "repohunter_adapters"

# System prompt — MUST match cloud_inference_api.py exactly
SYSTEM_PROMPT = (
    "You are RepoHunter, an expert AI assistant that recommends the best GitHub "
    "repositories for a user's specific needs. For each recommendation, provide "
    "the repository name, URL, star count, primary language, and a clear explanation "
    "of why it solves the user's requirement. Be concise and specific."
)

# ─── Data Loading ────────────────────────────────────────────────────────────
def load_training_data(data_path: str = None) -> Dataset:
    """
    Load training data from JSONL files.
    Expects {"text": "<|begin_of_text|>..."} format (Llama-3 chat template).
    Falls back to Firestore if no local files found.
    """
    # Try local reformatted files first
    candidates = [
        data_path,
        "train_llama3.jsonl",
        "/home/zeus/content/train_llama3.jsonl",
        "/home/zeus/content/github_repohunter/training/data/train_llama3.jsonl",
    ]

    for path in candidates:
        if path and os.path.exists(path):
            print(f"📂 Loading training data from: {path}")
            dataset = load_dataset("json", data_files=path, split="train")
            print(f"✅ Loaded {len(dataset)} samples.")
            return dataset

    # Fallback: try Firestore
    print("🌊 No local data found. Pulling from Firestore...")
    return load_from_firestore()


def load_from_firestore() -> Dataset:
    """Pull training data from Firestore refined_repositories and format it."""
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore

        KEY_PATH = "service-account.json"
        if not firebase_admin._apps:
            if not os.path.exists(KEY_PATH):
                print(f"❌ {KEY_PATH} not found. Upload your service account JSON.")
                sys.exit(1)
            cred = credentials.Certificate(KEY_PATH)
            firebase_admin.initialize_app(cred)

        db = firestore.client()
        docs = db.collection('refined_repositories').stream()

        samples = []
        for doc in docs:
            repo = doc.to_dict()
            instruction = repo.get('instruction', '')
            response = repo.get('output', '')

            if not instruction or not response:
                continue

            # Format as Llama-3 chat template
            text = (
                f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
                f"{SYSTEM_PROMPT}<|eot_id|>"
                f"<|start_header_id|>user<|end_header_id|>\n\n"
                f"{instruction}<|eot_id|>"
                f"<|start_header_id|>assistant<|end_header_id|>\n\n"
                f"{response}<|eot_id|>"
            )
            samples.append({"text": text})

        print(f"✅ Pulled {len(samples)} samples from Firestore.")
        return Dataset.from_list(samples)

    except Exception as e:
        print(f"❌ Firestore pull failed: {e}")
        sys.exit(1)


# ─── Training ────────────────────────────────────────────────────────────────
def train(data_path: str = None):
    print("=" * 60)
    print("🧬 RepoHunter Training — Unsloth Cloud Mode")
    print("=" * 60)

    # Step 1: Load model
    print(f"\n📦 Loading model: {MODEL_NAME}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        load_in_4bit=True,
    )

    # Step 2: Create LoRA adapter for training
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_alpha=16,
        lora_dropout=0,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )

    # Step 3: Load data
    dataset = load_training_data(data_path)

    if len(dataset) < 10:
        print(f"❌ Only {len(dataset)} samples — need at least 10 for meaningful training.")
        sys.exit(1)

    print(f"📊 Training samples: {len(dataset)}")

    # Step 4: Configure trainer
    # Adjust steps based on dataset size
    num_samples = len(dataset)
    max_steps = min(max(num_samples * 3, 200), 2000)  # 3 epochs, cap at 2000 steps

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=MAX_SEQ_LENGTH,
        dataset_num_proc=2,
        args=TrainingArguments(
            per_device_train_batch_size=2,
            gradient_accumulation_steps=4,
            warmup_steps=10,
            max_steps=max_steps,
            learning_rate=2e-4,
            fp16=not torch.cuda.is_bf16_supported(),
            bf16=torch.cuda.is_bf16_supported(),
            logging_steps=10,
            optim="adamw_8bit",
            weight_decay=0.01,
            lr_scheduler_type="cosine",
            seed=3407,
            output_dir="outputs",
            save_steps=100,
        ),
    )

    # Step 5: Train
    print(f"\n🚀 Starting training ({max_steps} steps)...")
    start_time = time.time()
    trainer.train()
    elapsed = time.time() - start_time
    print(f"\n✅ Training complete in {elapsed:.0f}s!")

    # Step 6: Save adapters
    print(f"\n💾 Saving adapters to {OUTPUT_DIR}/")
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print(f"✅ Adapters saved. Ready for inference!")
    print(f"\nTo use these adapters:")
    print(f"  1. Copy {OUTPUT_DIR}/ alongside cloud_inference_api.py")
    print(f"  2. Restart the inference server")


# ─── Entrypoint ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Train RepoHunter with Unsloth")
    parser.add_argument("--data", type=str, default=None,
                        help="Path to training JSONL (Llama-3 chat template format)")
    parser.add_argument("--continuous", action="store_true",
                        help="Run in continuous mode (wait for Firestore triggers)")
    args = parser.parse_args()

    if args.continuous:
        print("🛰️  Continuous training mode — waiting for triggers...")
        # Simple continuous loop
        while True:
            try:
                train(args.data)
                print("\n🛰️  Training cycle complete. Waiting 60s before next check...\n")
                time.sleep(60)
            except KeyboardInterrupt:
                print("\n👋 Stopped.")
                break
            except Exception as e:
                print(f"❌ Training error: {e}")
                time.sleep(30)
    else:
        train(args.data)
