import os
import sys
import subprocess
import time

class RepoHunterHub:
    def __init__(self):
        self.venv_python = "/Users/piyushdua/Desktop/instabot/venv/bin/python3"
        self.scripts_dir = "github_repohunter/scripts"
        self.base_dir = "/Users/piyushdua/Desktop/instabot"

    def header(self):
        os.system('clear')
        print("="*60)
        print("🏹 REPOHUNTER: INFINITE INTELLIGENCE HUB")
        print("="*60)
        print("Local Environment: Apple M4 (Optimized)")
        print(f"Cloud Backend: Lightning AI (SSH Tunnel: localhost:8000)")
        print("-" * 60)

    def run_script(self, path, desc):
        print(f"\n🚀 Launching {desc}...")
        try:
            subprocess.run([self.venv_python, path], cwd=self.base_dir)
        except KeyboardInterrupt:
            print("\n🛑 Stopped by user.")
        input("\nPress Enter to return to Hub...")

    def _update_env_value(self, key, value):
        env_path = os.path.join(self.base_dir, ".env")
        lines = []
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        updated = False
        new_lines = []
        for line in lines:
            if line.startswith(f"{key}="):
                new_lines.append(f"{key}={value}")
                updated = True
            else:
                new_lines.append(line)
        if not updated:
            new_lines.append(f"{key}={value}")
        with open(env_path, "w", encoding="utf-8") as f:
            f.write("\n".join(new_lines) + "\n")

    def test_expert_connection(self):
        print("\n📡 Testing Cloud Expert Connection...")
        # We try to ping the orchestrator's cloud endpoint
        from github_repohunter.orchestrator import RepoHunterOrchestrator
        orch = RepoHunterOrchestrator()
        if not orch.cloud_endpoint or "your-studio-id" in orch.cloud_endpoint:
            print("❌ ERROR: You haven't updated your Cloud URL in orchestrator.py yet!")
        else:
            res = orch.query_expert("Show me a popular repo for computer vision")
            print(f"✨ Expert Response Test: {res[:200]}...")
        input("\nPress Enter to return to Hub...")

    def generate_architecture_file(self):
        print("\n🧩 Generate architecture.md with parallel agents...")
        product = input("Product name: ").strip()
        requirement = input("Core requirement/problem statement: ").strip()
        if not product or not requirement:
            print("❌ Product name and requirement are required.")
            input("Press Enter...")
            return
        payload = {
            "product_name": product,
            "requirement": requirement,
            "write_file": True,
            "output_path": "architecture.md",
        }
        try:
            import requests
            res = requests.post("http://localhost:8000/architecture/generate", json=payload, timeout=120)
            if res.status_code == 200:
                print("✅ architecture.md generated at project root.")
            else:
                print(f"❌ Generation failed: {res.status_code} {res.text}")
        except Exception as exc:
            print(f"❌ Connection Error: {exc}")
        input("Press Enter...")

    def menu(self):
        while True:
            self.header()
            print("1. [GEN] Generate architecture.md (parallel agent mesh)")
            print("2. [SYNC] Sync Local Raw Data -> Cloud Firestore")
            print("3. [CLP] Start Continuous Learning Orchestrator (Infinite Loop)")
            print("4. [TEST] Ping Cloud Expert Model (Lightning AI)")
            print("5. [SETUP] Update Cloud Endpoint URL")
            print("q. Exit")
            
            choice = input("\nSelect an option: ").strip().lower()
            
            if choice == '1':
                self.generate_architecture_file()
            elif choice == '2':
                self.run_script("github_repohunter/scripts/cloud_sync.py", "Firestore Sync")
            elif choice == '3':
                self.run_script("github_repohunter/orchestrator.py", "Continuous Learning Loop")
            elif choice == '4':
                self.test_expert_connection()
            elif choice == '5':
                url = input("Enter your Lightning AI Studio URL: ").strip()
                if not url:
                    print("❌ URL cannot be empty.")
                else:
                    self._update_env_value("CLOUD_EXPERT_ENDPOINT", url)
                    self._update_env_value("REPOHUNTER_CLOUD_ENDPOINT", url)
                    print("✅ Cloud endpoint saved to .env (CLOUD_EXPERT_ENDPOINT).")
                input("Press Enter...")
            elif choice == 'q':
                print("👋 Happy hunting!")
                break

if __name__ == "__main__":
    hub = RepoHunterHub()
    hub.menu()
