import json
import random
import os

def prepare_data(input_file, output_dir):
    print(f"📂 Preparing data from {input_file}...")
    
    with open(input_file, 'r') as f:
        lines: list[str] = f.readlines()
    
    random.seed(42)
    random.shuffle(lines)
    
    num_lines = len(lines)
    train_end = int(num_lines * 0.8)
    val_end = int(num_lines * 0.9)
    
    train_data = lines[0:train_end]
    val_data = lines[train_end:val_end]
    test_data = lines[val_end:num_lines]
    
    os.makedirs(output_dir, exist_ok=True)
    
    with open(os.path.join(output_dir, 'train.jsonl'), 'w') as f:
        f.writelines(train_data)
    
    with open(os.path.join(output_dir, 'valid.jsonl'), 'w') as f:
        f.writelines(val_data)
    
    with open(os.path.join(output_dir, 'test.jsonl'), 'w') as f:
        f.writelines(test_data)
    
    print(f"✅ Data split complete:")
    print(f"  - Train: {len(train_data)} samples")
    print(f"  - Valid: {len(val_data)} samples")
    print(f"  - Test: {len(test_data)} samples")

if __name__ == "__main__":
    input_path = "github_repohunter/database/training/platinum_matchmaker.jsonl"
    output_path = "github_repohunter/training/data"
    
    if os.path.exists(input_path):
        prepare_data(input_path, output_path)
    else:
        print(f"⚠️ Input file not found: {input_path}")
