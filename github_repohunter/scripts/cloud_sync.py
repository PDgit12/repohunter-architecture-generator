import os
import json
import time
import subprocess
import sys
import importlib

# 1. Dependency Setup
def setup_dependencies():
    required = {"firebase-admin": "firebase_admin", "watchdog": "watchdog"}
    for pkg, import_name in required.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            print(f"📦 Installing missing dependency: {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

setup_dependencies()

# Linter Suppression: We import these inside functions to prevent IDE errors when packages aren't local.
# However, we can also use these placeholder types to help the linter if it can see them.
from typing import Any, List, Optional


class RepoSyncHandler: # We drop the inheritance here and use the observer's callback if needed, or import inside
    def __init__(self, db: Any, target_dir: str):
        from firebase_admin import firestore
        self.db = db
        self.target_dir = target_dir
        self.collection = db.collection('repositories')


    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            self._sync_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.json'):
            self._sync_file(event.src_path)

    def _sync_file(self, file_path: str):
        from firebase_admin import firestore
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)

            
            # Use filename as base for stable syncing
            base_id = os.path.basename(file_path).replace('.json', '')
            
            # Handle both single objects and lists of objects
            items = data if isinstance(data, list) else [data]
            batch = self.db.batch()
            
            refined_count = 0
            for i, item in enumerate(items):
                doc_id = f"{base_id}_{i}" if isinstance(data, list) else base_id
                
                # REFINEMENT: Format for Llama-3 Instruction Tuning
                # We expect the item to have 'name', 'language', 'description'
                name = item.get('name', 'Unknown Repo')
                lang = item.get('language', 'Unknown Language')
                desc = item.get('description', 'No description provided.')
                
                refined_data = {
                    "instruction": f"I need a GitHub repository for {name} ({lang}).",
                    "input": "",
                    "output": f"I recommend checking out {name}. It is written in {lang}. {desc}",
                    "metadata": item, # Keep original metadata for reference
                    "synced_at": firestore.SERVER_TIMESTAMP
                }
                
                batch.set(self.db.collection('refined_repositories').document(doc_id), refined_data)
                refined_count += 1
                
            batch.commit()
            print(f"📡 [Synced & Refined] {base_id} ({refined_count} items) -> Cloud Ocean (Refined)")
            
            # Check if we should signal a training threshold
            self._check_training_threshold()
                
        except Exception as e:
            print(f"❌ [Error Syncing {file_path}] {str(e)}")


    def _check_training_threshold(self):
        # Placeholder for trigger logic
        # In a real app, this could check Firestore counts or local state
        pass

def initial_catchup(db: Any, target_dir: str):
    from firebase_admin import firestore
    print("🧹 Starting initial catch-up sync...")
    collection = db.collection('repositories')
    files = [f for f in os.listdir(target_dir) if f.endswith('.json')]
    
    # Type hints to help the linter
    count: int = 0
    total_files: int = 0
    total_items: int = 0
    batch: Any = db.batch() 

    
    for filename in files:
        file_path = os.path.join(target_dir, filename)
        base_id = filename.replace('.json', '')
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            items_to_sync = data if isinstance(data, list) else [data]
            
            for i, item in enumerate(items_to_sync):
                doc_id = f"{base_id}_{i}" if isinstance(data, list) else base_id
                doc_ref = collection.document(doc_id)
                batch.set(doc_ref, item)
                count = count + 1
                total_items = total_items + 1
                
                if count >= 500:
                    batch.commit()
                    print(f"🚀 Committed batch of {count} assets...")
                    batch = db.batch()
                    count = 0
            
            total_files = total_files + 1
        except Exception as e:
            print(f"⚠️  Skipping {filename}: {str(e)}")
            
    if count > 0:
        batch.commit()
    
    print(f"✅ Catch-up complete! Total assets matched: {total_items}")

def start_realtime_sync():
    import firebase_admin
    from firebase_admin import credentials, firestore
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    project_id = "ai-task-mvp-7729"
    key_path = "service-account.json"
    target_dir = "github_repohunter/database/raw"

    if not firebase_admin._apps:
        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)

    db = firestore.client()

    # Step 1: Catch up existing files
    initial_catchup(db, target_dir)

    # Step 2: Establish Watcher
    # Local class to handle events
    class LocalHandler(FileSystemEventHandler):
        def __init__(self, handler):
            self.handler = handler
        def on_created(self, event):
            self.handler.on_created(event)
        def on_modified(self, event):
            self.handler.on_modified(event)

    sync_handler = RepoSyncHandler(db, target_dir)
    event_handler = LocalHandler(sync_handler)
    observer = Observer()
    observer.schedule(event_handler, target_dir, recursive=False)
    
    print(f"👀 Now watching {target_dir} for REAL-TIME updates...")
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_realtime_sync()
