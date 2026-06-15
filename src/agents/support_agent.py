import os
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

load_dotenv()
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL    = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")

# Load instruction from a txt file.
# Change INSTRUCTION_VERSION to "v1", "v2", or "v3" to try different prompt styles.
INSTRUCTION_VERSION = "v1"

_agents_dir = Path(__file__).parent
_instruction_file = _agents_dir / f"support_instructions_{INSTRUCTION_VERSION}.txt"
instruction = _instruction_file.read_text(encoding="utf-8")

# The agent uses Ollama via LiteLLM — no API key required.
model = LiteLlm(
    model=f"ollama/{OLLAMA_MODEL}",
    api_base=OLLAMA_BASE_URL,
)

root_agent = LlmAgent(
    name="eComBot_Support",
    model=model,
    instruction=instruction,
    description="Aureum Serpentis customer support agent. Handles product queries, order questions, and general support.",
)
