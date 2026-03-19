"""
RepoHunter Data Synthesizer v2 — High-Quality Training Pair Generation

Generates diverse, high-quality training pairs from repo metadata using:
  1. Groq / remote LLM API (fast, high quality)
  2. Local Ollama (fallback)

All output uses Llama-3 chat template to match inference format.
"""
import json
import os
import time
import random
import requests
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

REMOTE_LLM_URL = os.getenv("REMOTE_LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
SYNTHESIS_MODEL = os.getenv("SYNTHESIS_MODEL", "llama-3.3-70b-versatile")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

SYSTEM_PROMPT = (
    "You are RepoHunter, an expert AI assistant that recommends the best GitHub "
    "repositories for a user's specific needs. For each recommendation, provide "
    "the repository name, URL, star count, primary language, and a clear explanation "
    "of why it solves the user's requirement. Be concise and specific."
)

# ─── Diverse Query Templates ─────────────────────────────────────────────────
QUERY_TEMPLATES = [
    "I need a {language} library for {use_case}. What do you recommend?",
    "What's the best {language} project for {use_case}?",
    "Suggest a production-ready {language} tool for {use_case}",
    "I'm building a project that needs {use_case}. Any {language} repos?",
    "Find me a well-maintained {language} repository for {use_case}",
    "What {language} framework would work best for {use_case}?",
    "I need an open-source {language} solution for {use_case}",
    "Can you recommend a {use_case} library in {language} with good documentation?",
    "Looking for a lightweight {language} package for {use_case}",
    "Show me the top {language} repos for {use_case} with active maintenance",
]

SYNTHESIS_PROMPT = """You are a data generator for training an AI called RepoHunter.

Given a real GitHub repository's metadata, generate two things:
1. A realistic user question that this repository would perfectly answer
2. A detailed, expert-level answer recommending this repository

REPOSITORY DATA:
- Name: {name}
- URL: {url}
- Description: {description}
- Language: {language}
- Stars: {stars}
- License: {license}
- README excerpt: {readme}

RULES:
- The user question must sound natural and specific (not generic)
- The answer should explain WHY this repo fits, mention its stars, language, and key features
- Include the GitHub URL in the answer
- Be specific about technical strengths (not just "it's great")
- Vary your writing style — don't use the same structure every time

Return ONLY a JSON object with "question" and "answer" keys. No markdown, no extra text."""


# ─── LLM Backends ────────────────────────────────────────────────────────────
def generate_with_groq(prompt: str) -> str | None:
    """Use Groq (or any OpenAI-compatible API) for fast, high-quality generation."""
    if not LLM_API_KEY:
        return None

    headers = {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": SYNTHESIS_MODEL,
        "messages": [
            {"role": "system", "content": "You are a precise data generator. Only output valid JSON."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.8,
        "max_tokens": 600,
    }

    try:
        resp = requests.post(REMOTE_LLM_URL, headers=headers, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        elif resp.status_code == 429:
            print("  ⏳ Rate limited, waiting 10s...")
            time.sleep(10)
            return None
        else:
            print(f"  ⚠️ Groq error {resp.status_code}: {resp.text[:100]}")
            return None
    except Exception as e:
        print(f"  ⚠️ Groq request failed: {e}")
        return None


def generate_with_ollama(prompt: str) -> str | None:
    """Fallback: use local Ollama."""
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if resp.status_code == 200:
            return resp.json().get("response", "")
    except Exception:
        pass
    return None


def generate_pair(repo: dict) -> dict | None:
    """Generate a training pair for a given repo."""
    prompt = SYNTHESIS_PROMPT.format(
        name=repo.get("name", "Unknown"),
        url=repo.get("url", ""),
        description=repo.get("description", "No description"),
        language=repo.get("language", "Unknown"),
        stars=repo.get("stars", 0),
        license=repo.get("license", "Unknown"),
        readme=(repo.get("readme_snippet", "") or "")[:500],
    )

    # Try Groq first, fall back to Ollama
    raw = generate_with_groq(prompt) or generate_with_ollama(prompt)
    if not raw:
        return None

    try:
        # Clean up potential markdown wrapping
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]

        data = json.loads(raw)
        question = data.get("question", "")
        answer = data.get("answer", "")

        if not question or not answer or len(answer) < 30:
            return None

        return {"question": question, "answer": answer}
    except (json.JSONDecodeError, KeyError):
        return None


def to_llama3_text(question: str, answer: str) -> str:
    """Format as Llama-3 chat template."""
    return (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{SYSTEM_PROMPT}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{question}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
        f"{answer}<|eot_id|>"
    )


# ─── Main Synthesis ──────────────────────────────────────────────────────────
def synthesize(
    input_path: str = "github_repohunter/database/validated/global_ocean.jsonl",
    output_path: str = "github_repohunter/training/data/synthesized_llama3.jsonl",
    max_samples: int = None,
):
    """Synthesize training data from validated repos."""
    print("🧠 RepoHunter Data Synthesizer v2")
    print(f"📂 Input: {input_path}")
    print(f"📂 Output: {output_path}")
    print(f"🔗 LLM: {'Groq (' + SYNTHESIS_MODEL + ')' if LLM_API_KEY else 'Local Ollama'}")
    print()

    if not os.path.exists(input_path):
        print(f"❌ Input file not found: {input_path}")
        return

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # Load repos
    repos = []
    with open(input_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    repos.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    if max_samples:
        random.shuffle(repos)
        repos = repos[:max_samples]

    print(f"📊 Processing {len(repos)} repositories...\n")

    success = 0
    failed = 0

    with open(output_path, 'a') as f_out:
        for i, repo in enumerate(repos, 1):
            name = repo.get("name", "?")
            print(f"[{i}/{len(repos)}] {name}... ", end="", flush=True)

            pair = generate_pair(repo)
            if pair:
                text = to_llama3_text(pair["question"], pair["answer"])
                f_out.write(json.dumps({"text": text}) + "\n")
                f_out.flush()
                success += 1
                print("✅")
            else:
                failed += 1
                print("❌")

            # Rate limiting
            delay = 0.5 if LLM_API_KEY else 2.0
            time.sleep(delay)

    print(f"\n🎉 Synthesis complete!")
    print(f"  ✅ Success: {success}")
    print(f"  ❌ Failed: {failed}")
    print(f"  📂 Output: {output_path}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Synthesize RepoHunter training data")
    parser.add_argument("--input", type=str,
                        default="github_repohunter/database/validated/global_ocean.jsonl")
    parser.add_argument("--output", type=str,
                        default="github_repohunter/training/data/synthesized_llama3.jsonl")
    parser.add_argument("--max", type=int, default=None,
                        help="Max number of repos to process")
    args = parser.parse_args()

    synthesize(args.input, args.output, args.max)
