"""
RepoHunter Cloud Expert — Inference API (Unsloth + PEFT)
Runs on Lightning AI GPU. Serves recommendations via FastAPI.
"""
import os
import asyncio
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# ─── Config ───────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

EXPERT_API_KEY = os.getenv("EXPERT_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "unsloth/llama-3-8b-instruct-bnb-4bit")
MAX_SEQ_LENGTH = int(os.getenv("MAX_SEQ_LENGTH", "2048"))
MAX_NEW_TOKENS_CAP = int(os.getenv("MAX_NEW_TOKENS_CAP", "1024"))
WARMUP_INTERVAL_SEC = int(os.getenv("WARMUP_INTERVAL_SEC", "300"))

# Adapter path resolution — try multiple known locations
SCRIPT_DIR = Path(__file__).parent
CANDIDATE_ADAPTER_PATHS = [
    SCRIPT_DIR / "repohunter_adapters",                     # alongside this script
    SCRIPT_DIR.parent / "training" / "adapters",            # training output dir
    Path("/home/zeus/content/repohunter_adapters"),         # Lightning AI default
    Path("/home/zeus/content/github_repohunter/scripts/repohunter_adapters"),
]
ADAPTER_PATH = None
for p in CANDIDATE_ADAPTER_PATHS:
    if p.exists() and (p / "adapter_config.json").exists():
        ADAPTER_PATH = p
        break

# ─── Globals ──────────────────────────────────────────────────────────────────
model = None
tokenizer = None
load_error = None
logger = logging.getLogger("repohunter")
logging.basicConfig(level=logging.INFO)

try:
    import torch
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except Exception as e:
    torch = None
    DEVICE = "cpu"
    load_error = f"torch import failed: {e}"

# ─── System Prompt (single source of truth) ──────────────────────────────────
SYSTEM_PROMPT = (
    "You are RepoHunter, an expert AI assistant that recommends the best GitHub "
    "repositories for a user's specific needs. For each recommendation, provide "
    "the repository name, URL, star count, primary language, and a clear explanation "
    "of why it solves the user's requirement. Be concise and specific."
)

# ─── FastAPI ──────────────────────────────────────────────────────────────────
app = FastAPI(title="RepoHunter Expert Inference")


class QueryRequest(BaseModel):
    query: str
    max_tokens: int = 512
    temperature: float = 0.7


# ─── Model Loading (Pure HuggingFace, NO Unsloth) ────────────────────────────
def load_expert_model():
    """
    Load the base model and fine-tuned LoRA adapters natively using
    HuggingFace `transformers` and `peft`.
    This totally bypasses Unsloth's Triton kernels that cause KV cache bugs
    on Tesla T4 GPUs during generation.
    """
    global model, tokenizer, load_error

    if model is not None:
        return model, tokenizer

    logger.info(f"🚀 Loading base model natively: {MODEL_NAME} on {DEVICE}...")

    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel

        # Fast loading configuration
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        )

        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, legacy=False)
        tokenizer.pad_token_id = tokenizer.eos_token_id

        logger.info(f"Downloading/Loading 4-bit precision base weights...")
        base_model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            quantization_config=bnb_config,
            device_map="auto",
        )

        if ADAPTER_PATH and ADAPTER_PATH.exists():
            logger.info(f"🧬 Injecting LoRA adapters from {ADAPTER_PATH}")
            model = PeftModel.from_pretrained(base_model, str(ADAPTER_PATH))
            logger.info("✅ Adapters merged successfully.")
        else:
            logger.warning("⚠️ No adapter path found. Running purely as base model.")
            model = base_model

        model.eval()
        logger.info("✨ RepoHunter Expert is ready for inference (Native HF mode).")

    except Exception as e:
        load_error = f"Model load failed: {e}"
        logger.error(f"❌ CRITICAL: {load_error}")
        import traceback
        traceback.print_exc()
        return None, None

    return model, tokenizer


# ─── Startup ────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up FastAPI and loading expert model...")
    load_expert_model()
    logger.info("Model load complete. Ready to serve requests.")

# ─── Security Middleware ──────────────────────────────────────────────────────
@app.middleware("http")
async def verify_expert_key(request: Request, call_next):
    if not EXPERT_API_KEY:
        return JSONResponse(
            status_code=503,
            content={"detail": "Server not configured: EXPERT_API_KEY missing"},
        )
    if request.url.path == "/recommend":
        api_key = request.headers.get("X-API-Key")
        if api_key != EXPERT_API_KEY:
            return JSONResponse(
                status_code=401,
                content={"detail": "Unauthorized: Invalid API Key"},
            )
    return await call_next(request)


# ─── Routes ──────────────────────────────────────────────────────────────────
@app.get("/health")
async def health_check():
    if load_error:
        return {"status": "error", "error": load_error}
    if model is None:
        return {"status": "loading", "device": DEVICE, "adapter": str(ADAPTER_PATH)}
    return {"status": "ready", "device": DEVICE, "adapter": str(ADAPTER_PATH)}


@app.post("/recommend")
async def recommend(request: QueryRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model is still loading.")
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty")
    if len(request.query) > 4000:
        raise HTTPException(status_code=400, detail="query too long (max 4000 chars)")

    max_gen = min(request.max_tokens, MAX_NEW_TOKENS_CAP)

    # ── Build prompt using the SAME Llama-3 chat template as training ──
    prompt = (
        f"<|begin_of_text|><|start_header_id|>system<|end_header_id|>\n\n"
        f"{SYSTEM_PROMPT}<|eot_id|>"
        f"<|start_header_id|>user<|end_header_id|>\n\n"
        f"{request.query}<|eot_id|>"
        f"<|start_header_id|>assistant<|end_header_id|>\n\n"
    )

    try:
        inputs = tokenizer([prompt], return_tensors="pt").to(DEVICE)

        if torch is None:
            raise RuntimeError("torch not available")

        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_gen,
                use_cache=False,
                do_sample=request.temperature > 0,
                temperature=max(request.temperature, 0.01),
                pad_token_id=tokenizer.eos_token_id,
            )

        full_response = tokenizer.batch_decode(outputs)[0]
        # Extract only the assistant's reply
        answer = full_response.split("<|start_header_id|>assistant<|end_header_id|>")[-1]
        answer = answer.replace("<|eot_id|>", "").replace("<|end_of_text|>", "").strip()

        return {"recommendation": answer}

    except Exception as e:
        logger.error(f"❌ Generation error: {e}")
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")


# ─── Entrypoint ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if torch is None or not torch.cuda.is_available():
        logger.error("❌ CRITICAL: No GPU detected. Unsloth requires CUDA.")
    uvicorn.run(app, host="0.0.0.0", port=8080)
