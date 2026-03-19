import requests
import json

class OllamaClient:
    def __init__(self, model="llama3", base_url="http://localhost:11434"):
        self.model = model
        self.base_url = f"{base_url}/api/generate"

    def generate_response(self, prompt):
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        try:
            print(f"🤖 Thinking (Model: {self.model})...")
            response = requests.post(self.base_url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
        except requests.exceptions.ConnectionError:
            return "❌ Error: Ollama is not running! Make sure to run 'ollama serve' in your terminal."
        except Exception as e:
            return f"❌ Error: {str(e)}"

if __name__ == "__main__":
    ai = OllamaClient(model="llama3")
    test_prompt = "Summarize why quantization is important for local LLMs in one sentence."
    answer = ai.generate_response(test_prompt)
    print(f"\nPrompt: {test_prompt}")
    print(f"Ollama: {answer}")
