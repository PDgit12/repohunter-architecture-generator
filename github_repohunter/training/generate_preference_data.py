import json
import os
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def load_env_manual(path=".env"):
    if os.path.exists(path):
        with open(path, "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    os.environ[key] = value

class DPODataGenerator:
    def __init__(self):
        load_env_manual()
        self.remote_url = os.getenv("REMOTE_LLM_URL", "https://api.groq.com/openai/v1/chat/completions")
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.model_name = "llama-3.3-70b-versatile"
        
        self.input_path = "github_repohunter/database/training/platinum_matchmaker.jsonl"
        self.output_path = "github_repohunter/training/data/dpo_preferences.jsonl"
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def generate_rejected_response(self, instruction, chosen_response):
        """
        Uses a technical critic to generate a 'Rejected' version of a response.
        The rejected version should be a 'yes man' response: overly vague, 
        polite but uninformative, or slightly hallucinated.
        """
        prompt = f"""
        You are a technical critic for an AI training pipeline.
        I will provide an instruction and a high-quality (CHOSEN) response.
        Your task is to generate a REJECTED version of the response.
        
        A REJECTED response should:
        1. Be a "yes man" - agree with everything but provide no technical depth.
        2. Be overly vague (e.g., "This repo is great for your needs!").
        3. Lack specific details found in the CHOSEN response (like URLs or specific feature names).
        4. Be polite but ultimately useless for a developer.
        
        Instruction: {instruction}
        CHOSEN Response: {chosen_response}
        
        ONLY return the REJECTED response text. Do not add any preamble.
        """
        
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}]
        }
        
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            response = requests.post(self.remote_url, json=payload, headers=headers, timeout=60)
            if response.status_code == 200:
                result = response.json()['choices'][0]['message']['content'].strip()
                return result
        except Exception as e:
            print(f"⚠️ DPO generation failed: {e}")
        return None

    def process_sample(self, sample):
        text = sample['text']
        # Split instruction and response
        parts = text.split(" ### Response: ")
        if len(parts) != 2:
            return None
            
        instruction = parts[0].replace("### Instruction: ", "").strip()
        chosen = parts[1].strip()
        
        rejected = self.generate_rejected_response(instruction, chosen)
        if rejected:
            return {
                "prompt": instruction,
                "chosen": chosen,
                "rejected": rejected
            }
        return None

    def run(self, limit=100):
        if not os.path.exists(self.input_path):
            print("❌ Platinum dataset not found.")
            return

        samples = []
        with open(self.input_path, 'r') as f:
            for line in f:
                samples.append(json.loads(line))

        print(f"🧪 Generating preference data for {min(len(samples), limit)} samples...")
        
        count = 0
        with open(self.output_path, 'w') as f_out:
            with ThreadPoolExecutor(max_workers=10) as executor:
                future_to_sample = {executor.submit(self.process_sample, s): s for s in samples[:limit]}
                for future in as_completed(future_to_sample):
                    result = future.result()
                    if result:
                        f_out.write(json.dumps(result) + "\n")
                        count += 1
                        if count % 10 == 0:
                            print(f"✅ Generated {count} preference pairs...")

        print(f"🏁 Finished! DPO dataset saved to {self.output_path}")

if __name__ == "__main__":
    generator = DPODataGenerator()
    generator.run(limit=50) # Start with 50 samples for the POC
