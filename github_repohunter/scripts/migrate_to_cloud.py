import os
import json
import firebase_admin
from firebase_admin import credentials, firestore

def migrate():
    # Attempt to initialize with default credentials (CLI login)
    project_id = "ai-task-mvp-7729"
    
    if not firebase_admin._apps:
        try:
            # First try service account if it exists
            key_path = "service-account.json"
            if os.path.exists(key_path):
                cred = credentials.Certificate(key_path)
                firebase_admin.initialize_app(cred)
                print(f"✅ Authenticated via Service Account: {project_id}")
            else:
                # Fallback to default
                firebase_admin.initialize_app(options={'projectId': project_id})
                print(f"✅ Authenticated with project: {project_id}")
        except Exception as e:
            print(f"❌ Authentication failed: {e}")
            print("💡 TIP: Please place your 'service-account.json' in the project root.")
            return

    db = firestore.client()
    
    # Load local data
    data_path = "github_repohunter/database/validated/master_dataset.json"
    if not os.path.exists(data_path):
        print(f"❌ Local data not found: {data_path}")
        return
        
    with open(data_path, 'r') as f:
        repos = json.load(f)
        
    print(f"🚀 Migrating {len(repos)} repositories to Firestore...")
    
    batch = db.batch()
    count = 0
    
    for repo in repos:
        # Create a document ID based on the repo name (sanitized)
        doc_id = repo['name'].replace('/', '---')
        doc_ref = db.collection('repositories').document(doc_id)
        batch.set(doc_ref, repo)
        count += 1
        
        # Firestore batch limit is 500
        if count % 400 == 0:
            batch.commit()
            batch = db.batch()
            print(f"📦 Committed {count} records...")
            
    batch.commit()
    print(f"✅ Migration Complete! {count} repositories moved to the Cloud Ocean.")

if __name__ == "__main__":
    migrate()
