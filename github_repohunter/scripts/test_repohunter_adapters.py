from mlx_lm import load, generate
import os

# Configuration
# This script is a LOCAL REFERENCE for Apple Silicon M4.
# It does NOT use CUDA. It uses MLX (Metal Performance Shaders).
BASE_MODEL = "unsloth/Llama-3-8B-Instruct-bnb-4bit" 
ADAPTER_PATH = os.path.join(os.path.dirname(__file__), "repohunter_adapters")

def run_mlx_inference(query):
    print(f"🚀 Loading RepoHunter (Expert Mode) via MLX (Local Mac)...")
    
    try:
        # Load model and tokenizer with adapters
        model, tokenizer = load(
            BASE_MODEL,
            adapter_path=ADAPTER_PATH
        )
        
        prompt = f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\nYou are RepoHunter, an expert AI that recommends the best GitHub repositories based on user needs.<|eot_id|><|start_header_id|>user<|end_header_id|>\n\n{query}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
        
        print(f"\nQuery: {query}")
        print("\nRepoHunter (MLX) Recommendation:")
        print("-" * 30)
        
        response = generate(
            model, 
            tokenizer, 
            prompt=prompt, 
            max_tokens=512,
            verbose=True
        )
        
        return response
    except Exception as e:
        return f"❌ MLX Inference Error: {e}"

if __name__ == "__main__":
    test_query = "I need a high-performance HTTP server library for Python."
    result = run_mlx_inference(test_query)
    if "❌" in result:
        print(result)
