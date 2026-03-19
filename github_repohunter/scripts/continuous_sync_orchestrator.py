import os
import sys
import subprocess
import time
import importlib

# 1. Dependency Setup
def setup_dependencies():
    required = {"firebase-admin": "firebase_admin"}
    for pkg, import_name in required.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            print(f"📦 Installing missing dependency: {pkg}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])

setup_dependencies()

setup_dependencies()

# Linter Suppression: Global imports moved to method scope
from typing import Any


class ContinuousLearningOrchestrator:
    def __init__(self, project_id: str, threshold: int = 500):
        from firebase_admin import firestore
        self.project_id = project_id
        self.threshold = threshold
        self.db = firestore.client()
        self.trigger_collection = self.db.collection('training_triggers')
        self.data_collection = self.db.collection('refined_repositories')

        
    def monitor_and_trigger(self):
        print(f"🕵️‍♂️ Continuous Learning Orchestrator is active.")
        print(f"📊 Monitoring threshold: {self.threshold} new repositories.")
        
        while True:
            try:
                # 1. Check current volume of refined data
                # We can store a 'last_trained_count' in a config doc
                config_ref = self.db.collection('config').document('learning_stats')
                config = config_ref.get().to_dict() or {"last_trained_count": 0}
                
                # Get current total count (optimized via metadata or count query)
                current_count = self.data_collection.count().get()[0][0].value
                
                new_data_count = current_count - config['last_trained_count']
                
                if new_data_count >= self.threshold:
                    print(f"🚀 Threshold Reached! {new_data_count} new repos detected.")
                    self._trigger_training(current_count)
                    # Update stats
                    config_ref.set({"last_trained_count": current_count}, merge=True)
                else:
                    print(f"💤 Pending: {new_data_count}/{self.threshold} new repos... (Checked at {time.strftime('%H:%M:%S')})")
                
                # Check every 5 minutes to avoid excessive queries
                time.sleep(300) 
                
            except Exception as e:
                print(f"❌ Orchestrator Error: {e}")
                time.sleep(60)

    def _trigger_training(self, total_count):
        trigger_id = f"trigger_{int(time.time())}"
        trigger_data = {
            "status": "PENDING",
            "reason": f"Data threshold reached ({total_count} total)",
            "requested_at": firestore.SERVER_TIMESTAMP,
            "total_samples": total_count
        }
        self.trigger_collection.document(trigger_id).set(trigger_data)
        print(f"🔥 SIGNAL SENT: {trigger_id} is now in Cloud Ocean.")

    orchestrator = ContinuousLearningOrchestrator(project_id="ai-task-mvp-7729", threshold=100) # Lowered for testing
    orchestrator.monitor_and_trigger()

