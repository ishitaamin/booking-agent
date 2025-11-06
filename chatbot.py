# chatbot.py
import os
import json
import logging
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class LLMOut(BaseModel):
    reply: str
    set: Dict[str, Any] = Field(default_factory=dict)
    action: Dict[str, Any] = Field(default_factory=dict)

def _extract_json_balanced(text: str) -> str:
    text = text.strip()
    start = text.find("{")
    if start == -1:
        return ""
    depth = 0
    for idx in range(start, len(text)):
        ch = text[idx]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:idx + 1]
    return ""

async def llm_reply(user_message: str, stage: str, context: dict, session: dict) -> dict:
    system = (
        "You are MovieBot, a friendly WhatsApp assistant that books movie tickets. "
        "You MUST OUTPUT ONLY valid JSON with keys: 'reply' (string), 'set' (object), 'action' (object). "
        "ALWAYS include available options from context when asking. "
        "- At 'greeting' stage → list all movies with numbering from context['movies']. "
        "- At 'ask_time' stage → ALWAYS list showtimes from context['showtimes'] in bullet points.\n"
        "- Each showtime line must include: startTime, duration, screenName, available_count, and price.\n"
        "- At 'ask_seats' stage → ALWAYS list available seats from context['showtimes'][0]['seats'] in bullet points. \n"
        "Never just say 'checking availability', always display real data. "
        "If user says something irrelevant, politely redirect."
    )

    prompt_user = {
        "stage": stage,
        "session": session,
        "context": context,
        "user_message": user_message,
        "instructions": (
            "Produce ONLY a JSON object with keys 'reply' (string), 'set' (object), 'action' (object). "
            "If no keys should be set, use {}. Use stage to decide what to ask next. Use ltm to personalize."
        )
    }

    user_prompt = json.dumps(prompt_user, default=str)

    attempts = 2
    for attempt in range(attempts):
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(f"{system}\nUser payload:\n{user_prompt}")
            raw = response.text.strip()
            jtxt = _extract_json_balanced(raw)
            if not jtxt:
                raise ValueError("No JSON object found in LLM output")
            parsed = json.loads(jtxt)
            validated = LLMOut.model_validate(parsed)
            return validated.model_dump()
        except (json.JSONDecodeError, ValidationError, ValueError) as e:
            logger.warning("LLM returned invalid JSON (attempt %d/%d): %s", attempt + 1, attempts, e)
            if attempt < attempts - 1:
                system += "\nIMPORTANT: Respond ONLY with valid JSON object, nothing else."
                continue
            return {"reply": "Sorry, I couldn't process that. Could you rephrase?", "set": {}, "action": {}}
        except Exception:
            logger.exception("LLM error")
            return {"reply": "Sorry, something went wrong on my side.", "set": {}, "action": {}}


