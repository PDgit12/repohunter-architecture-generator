import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def synthesize():
    project_id = "ai-task-mvp-7729"
    key_path = "service-account.json"
    output_path = "github_repohunter/database/training/platinum_v2.jsonl"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)

    db = firestore.client()
    repos_ref = db.collection('repositories')
    
    print("🌊 Pulling tech assets from the Cloud Ocean...")
    docs = repos_ref.stream()
    
    count = 0
    with open(output_path, 'w') as f:
        for doc in docs:
            repo = doc.to_dict()
            name = repo.get('name', 'Unknown')
            desc = repo.get('description', 'No description.')
            lang = repo.get('language', 'Various')
            url = repo.get('url', '')
            
            # Synthesize Instruction-Response pair
            instruction = f"Recommend a {lang} repository for {desc[:100]}..."
            response = f"I recommend '{name}'. It is a {lang} project described as: {desc}. You can find it at {url}. This project is ideal for developers looking for high-quality {lang} implementations."
            
            sample = {
                "text": f"### Instruction: {instruction} ### Response: {response}"
            }
            
            f.write(json.dumps(sample) + "\n")
            count += 1
            if count % 500 == 0:
                print(f"🧠 Synthesized {count} training pairs...")

    print(f"✅ Synthesis Complete! {count} pairs ready for fine-tuning at {output_path}")

if __name__ == "__main__":
    synthesize()
