import os
import re
from pathlib import Path
from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from src.tools.order_tools import get_order_status, cancel_order
from src.tools.product_tools import lookup_product

load_dotenv()

OPENROUTER_API_KEY  = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL    = os.getenv("OPENROUTER_MODEL", "openrouter/google/gemini-2.5-flash")
INSTRUCTION_VERSION = os.getenv("INSTRUCTION_VERSION", "v1")

_dir = Path(__file__).parent
_instruction_file = _dir / "agents" / f"support_instructions_{INSTRUCTION_VERSION}.txt"
base_instruction = _instruction_file.read_text(encoding="utf-8")


full_instruction = base_instruction


def extract_and_inject_session(callback_context: CallbackContext, llm_request: LlmRequest) -> None:
    """Extract name/order ID from user message and inject into system prompt."""
    state = callback_context.state

    last_user_text = ""
    for content in reversed(llm_request.contents or []):
        if hasattr(content, "role") and content.role == "user":
            if content.parts:
                last_user_text = content.parts[0].text or ""
            break

    if last_user_text:
        order_match = re.search(r'\bORD-\d+\b', last_user_text, re.IGNORECASE)
        if order_match:
            state["last_order_id"] = order_match.group(0).upper()

        name_match = re.search(
            r"(?:my name is|i am|i'm|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)",
            last_user_text, re.IGNORECASE
        )
        if name_match:
            state["customer_name"] = name_match.group(1).strip()

    # Inject session memory into system prompt
    name     = state.get("customer_name")
    order_id = state.get("last_order_id")
    if not name and not order_id:
        return

    lines = ["\n## Session Memory"]
    if name:
        lines.append(f"- Customer name: {name}. Use their name naturally.")
    if order_id:
        lines.append(f"- Last order mentioned: {order_id}. Do not ask for it again.")

    enriched = full_instruction + "\n".join(lines)
    for content in llm_request.contents or []:
        if hasattr(content, "role") and content.role == "system":
            if content.parts:
                content.parts[0].text = enriched
            return


model = LlmAgent(
    name="eComBot_Support",
    model=LiteLlm(
        model=OPENROUTER_MODEL,
        api_key=OPENROUTER_API_KEY,
        api_base="https://openrouter.ai/api/v1",
    ),
    instruction=full_instruction,
    description="eComBot electronics customer support agent.",
    before_model_callback=extract_and_inject_session,
    tools=[get_order_status, cancel_order, lookup_product],
)

root_agent = model
