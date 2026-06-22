"""
Simple keyword-based model router.
Complex queries (complaints, comparisons, cancellations) → DEEP_MODEL.
Everything else → FAST_MODEL.
Falls back to FAST_MODEL if DEEP_MODEL fails.
"""
import os
import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

FAST_MODEL     = os.getenv("FAST_MODEL",     "ollama/mistral")
DEEP_MODEL     = os.getenv("DEEP_MODEL",     "ollama/mistral")
OLLAMA_BASE    = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
LOG_FILE       = Path(__file__).parent.parent.parent / "logs" / "routing.log"

COMPLEX_KEYWORDS = {
    "compare", "recommend", "complaint", "refund",
    "cancel", "broken", "damage", "vs", "better", "worse", "difference"
}

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)


def classify(message: str) -> str:
    words = set(message.lower().split())
    return "deep" if words & COMPLEX_KEYWORDS else "fast"


def call_model(messages: list, user_message: str) -> str:
    import litellm
    complexity = classify(user_message)
    model      = DEEP_MODEL if complexity == "deep" else FAST_MODEL

    logging.info(f"complexity={complexity} model={model} query={user_message[:60]}")

    try:
        resp = litellm.completion(
            model=model, messages=messages, api_base=OLLAMA_BASE
        )
        return resp.choices[0].message.content
    except Exception as e:
        logging.warning(f"deep model failed ({e}), falling back to {FAST_MODEL}")
        resp = litellm.completion(
            model=FAST_MODEL, messages=messages, api_base=OLLAMA_BASE
        )
        return resp.choices[0].message.content
