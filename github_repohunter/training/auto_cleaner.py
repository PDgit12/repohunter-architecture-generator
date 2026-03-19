import pandas as pd
import json
import os

def clean_and_export(input_file, output_file):
    if not os.path.exists(input_file):
        print(f"⚠️ Input {input_file} not found.")
        return False
        
    print(f"🧹 Cleaning dataset: {input_file}...")
    
    data = []
    with open(input_file, 'r') as f:
        for line in f:
            try:
                data.append(json.loads(line))
            except: continue

    if not data:
        return False

    df = pd.DataFrame(data)
    
    # Cleaning Heuristics
    initial_count = len(df)
    df = df.drop_duplicates(subset=['text'])
    
    df['length'] = df['text'].apply(len)
    df = df[df['length'] >= 300]
    
    # Strip conversational prefixes
    junk_prefixes = ["Certainly!", "Here is", "I recommend", "This repository"]
    for prefix in junk_prefixes:
        df['text'] = df['text'].str.replace(f"### Response: {prefix}", "### Response: ", case=False)

    df[['text']].to_json(output_file, orient='records', lines=True)
    print(f"✅ Cleaned: {initial_count} -> {len(df)} pairs saved to {output_file}")
    return True

if __name__ == "__main__":
    input_f = 'github_repohunter/database/training/matchmaker_pairs.jsonl'
    output_f = 'github_repohunter/database/training/platinum_matchmaker.jsonl'
    clean_and_export(input_f, output_f)
