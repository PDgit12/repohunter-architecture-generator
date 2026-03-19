"""
Reformat existing Alpaca-format training data to Llama-3 chat template.

Reads:  training/data/train.jsonl  (7,608 samples in ### Instruction / ### Response format)
Writes: training/data/train_llama3.jsonl  (same data, Llama-3 chat template)

This ensures training data matches inference prompt format exactly.
"""
import json
import re
import os
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
TRAINING_DATA_DIR = SCRIPT_DIR.parent / "training" / "data"

INPUT_FILES = {
    "train": TRAINING_DATA_DIR / "train.jsonl",
    "valid": TRAINING_DATA_DIR / "valid.jsonl",
    "test":  TRAINING_DATA_DIR / "test.jsonl",
}

SYSTEM_PROMPT = (
    "You are RepoHunter, an expert AI assistant that recommends the best GitHub "
    "repositories for a user's specific needs. For each recommendation, provide "
    "the repository name, URL, star count, primary language, and a clear explanation "
    "of why it solves the user's requirement. Be concise and specific."
)


def parse_alpaca_text(text: str) -> tuple[str, str]:
    """
    Parse an Alpaca-format text field into (instruction, response).
    Handles both:
      - "### Instruction: ... ### Response: ..."
      - "<|begin_of_text|>...<|start_header_id|>user... (already Llama-3 format)"
    """
    # Already in Llama-3 format? Extract user + assistant parts
    if "<|start_header_id|>user<|end_header_id|>" in text:
        user_match = re.search(
            r'<\|start_header_id\|>user<\|end_header_id\|>\s*\n*\n*(.*?)<\|eot_id\|>',
            text, re.DOTALL
        )
        assistant_match = re.search(
            r'<\|start_header_id\|>assistant<\|end_header_id\|>\s*\n*\n*(.*?)(?:<\|eot_id\|>|$)',
            text, re.DOTALL
        )
        instruction = user_match.group(1).strip() if user_match else ""
        response = assistant_match.group(1).strip() if assistant_match else ""
        return instruction, response

    # Alpaca format: ### Instruction: ... ### Response: ...
    parts = re.split(r'###\s*Response:\s*', text, maxsplit=1)
    if len(parts) == 2:
        instruction_block = parts[0]
        response = parts[1].strip()

        # Clean up instruction
        instruction = re.sub(r'^.*?###\s*Instruction:\s*', '', instruction_block, flags=re.DOTALL).strip()
        return instruction, response

    # Fallback: treat entire text as response
    return "", text.strip()


def to_llama3_chat(instruction: str, response: str) -> str:
    """Convert an instruction/response pair to Llama-3 chat template."""
    return (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{SYSTEM_PROMPT}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{instruction}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        f"{response}<|eot_id|>"
    )


def reformat_file(input_path: Path, output_path: Path) -> int:
    """Reformat a single JSONL file. Returns count of converted samples."""
    if not input_path.exists():
        print(f"⚠️  Skipping (not found): {input_path}")
        return 0

    converted = 0
    skipped = 0

    with open(input_path, 'r') as f_in, open(output_path, 'w') as f_out:
        for line_num, line in enumerate(f_in, 1):
            line = line.strip()
            if not line:
                continue

            try:
                data = json.loads(line)
                text = data.get("text", "")

                instruction, response = parse_alpaca_text(text)

                # Skip empty/garbage samples
                if not instruction or not response or len(response) < 20:
                    skipped += 1
                    continue

                # Skip samples that are just template parroting
                if response.startswith("I recommend '") and "This project is ideal" in response:
                    # Keep but improve - these are low quality but still usable
                    pass

                new_text = to_llama3_chat(instruction, response)
                f_out.write(json.dumps({"text": new_text}) + "\n")
                converted += 1

            except (json.JSONDecodeError, Exception) as e:
                print(f"  ⚠️  Line {line_num}: {e}")
                skipped += 1

    print(f"  ✅ {converted} converted, {skipped} skipped → {output_path.name}")
    return converted


def main():
    print("🔄 Reformatting training data to Llama-3 chat template...")
    print(f"📂 Data directory: {TRAINING_DATA_DIR}\n")

    total = 0
    for split_name, input_path in INPUT_FILES.items():
        output_path = input_path.parent / f"{split_name}_llama3.jsonl"
        print(f"📄 Processing {split_name}...")
        count = reformat_file(input_path, output_path)
        total += count

    print(f"\n🎉 Done! {total} total samples reformatted to Llama-3 chat template.")
    print("\nNext steps:")
    print("  1. Upload the *_llama3.jsonl files to Lightning AI")
    print("  2. Run the updated cloud_train_unsloth.py to retrain")
    print("  3. Test inference with the new adapters")


if __name__ == "__main__":
    main()
