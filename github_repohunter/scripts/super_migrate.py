import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def super_migrate():
    project_id = "ai-task-mvp-7729"
    key_path = "service-account.json"
    raw_dir = "github_repohunter/database/raw"
    
    if not os.path.exists(key_path):
        print(f"❌ Service account key not found: {key_path}")
        return

    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
        print(f"✅ Authenticated via Service Account: {project_id}")

    db = firestore.client()
    
    # Get all JSON files in raw_dir
    raw_files = [f for f in os.listdir(raw_dir) if f.endswith('.json')]
    print(f"🔍 Found {len(raw_files)} raw files to ingest.")
    
    total_migrated = 0
    batch = db.batch()
    batch_count = 0
    
    for filename in raw_files:
        filepath = os.path.join(raw_dir, filename)
        try:
            with open(filepath, 'r') as f:
                repos = json.load(f)
                
            if not isinstance(repos, list):
                continue
                
            for repo in repos:
                # Sanitize name for document ID
                if 'name' not in repo:
                    continue
                    
                doc_id = repo['name'].replace('/', '---')
                doc_ref = db.collection('repositories').document(doc_id)
                
                batch.set(doc_ref, repo)
                batch_count += 1
                total_migrated += 1
                
                # Firestore batch limit is 500
                if batch_count >= 400:
                    batch.commit()
                    batch = db.batch()
                    batch_count = 0
                    print(f"📦 Committed {total_migrated} repositories...")
                    
        except Exception as e:
            print(f"⚠️ Error processing {filename}: {e}")
            continue
            
    # Final commit
    if batch_count > 0:
        batch.commit()
        
    print(f"✅ Multi-Phase Migration Complete!")
    print(f"🌊 Total Ocean Volume: {total_migrated} repositories.")

if __name__ == "__main__":
    super_migrate()
