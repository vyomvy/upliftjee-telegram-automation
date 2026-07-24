from google import genai
from google.genai import types
from config import SYSTEM_PROMPT
import re
import asyncio
import logging

logger = logging.getLogger(__name__)

# ================== CREDENTIALS (CHANGE THESE LOCALLY) ==================
PROJECT_ID = "YOUR_PROJECT_ID_HERE"          # ← Put your real Project ID here when running locally
LOCATION = "us-central1"

# Initialize client - Replace with your credentials when running
client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
MODEL_ID = "gemini-2.5-flash"

conversation_history = {}

# ─── Keywords for dynamic thinking budget (original logic) ───
SIMPLE_KEYWORDS = [
    "book", "course", "test", "fees", "price", "join", "enroll",
    "hello", "hi", "hii", "hey", "thanks", "thank you", "shukriya",
    "ok", "okay", "haan", "nahi", "theek", "accha", "bye", "good morning",
    "good night", "kya hal", "namaste", "link", "admission"
]

HARD_KEYWORDS = [
    "prove", "proof", "integrate", "differentiate", "derivation", "derive",
    "advanced", "jee adv", "jee advanced", "difficult", "hard", "complex",
    "limit", "continuity", "determinant", "matrix", "vector", "3d",
    "probability", "permutation", "combination", "binomial", "series",
    "convergence", "complex number", "iupac", "mechanism", "thermodynamics",
    "equilibrium", "electrochemistry", "organic", "inorganic"
]


def get_thinking_budget(message, image):
    """
    Message type ke hisaab se thinking budget.
    """
    if image:
        return 8000

    msg = (message or "").lower()

    if any(w in msg for w in SIMPLE_KEYWORDS):
        return 1024

    if any(w in msg for w in HARD_KEYWORDS):
        return 8000

    return 4000


def clean_reply(text):
    """
    AI reply se unwanted LaTeX, code blocks etc. clean karo.
    """
    text = text.replace("💪", "")

    text = re.sub(r'\$\$(.+?)\$\$', lambda m: m.group(1).strip(), text, flags=re.DOTALL)
    text = re.sub(r'\$(.+?)\$', lambda m: m.group(1).strip(), text)

    text = re.sub(r'```[\w]*\n?', '', text)
    text = re.sub(r'```', '', text)
    text = re.sub(r'`(.+?)`', lambda m: m.group(1), text)

    text = re.sub(r'\\frac\{(.+?)\}\{(.+?)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\\sqrt\{(.+?)\}', r'sqrt(\1)', text)
    text = re.sub(r'\\int', 'integral', text)
    text = re.sub(r'\\sum', 'sum', text)
    text = re.sub(r'\\infty', 'infinity', text)
    text = re.sub(r'\\[a-zA-Z]+\{?', '', text)
    text = re.sub(r'\{|\}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


async def get_ai_response(user_id, message, image=None):
    """
    Main AI response function - async version.
    """
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    history = conversation_history[user_id]

    budget = get_thinking_budget(message, image)
    logger.info(f"🧠 Thinking budget: {budget} — {'Image' if image else (message[:50] if message else '[empty]')}")

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        thinking_config=types.ThinkingConfig(
            thinking_budget=budget
        )
    )

    sdk_history = []
    for msg in history:
        role = "user" if msg["role"] == "user" else "model"
        sdk_history.append(
            types.Content(
                role=role,
                parts=[types.Part(text=msg["content"])]
            )
        )

    max_retries = 4
    wait_seconds = 5

    for attempt in range(max_retries):
        try:
            if image:
                try:
                    image_bytes = image.getvalue()
                    contents = sdk_history + [
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(inline_data=types.Blob(mime_type="image/jpeg", data=image_bytes)),
                                types.Part(text=message if message else "Is image ka question text mein samjhao.")
                            ]
                        )
                    ]
                except Exception:
                    contents = sdk_history + [types.Content(role="user", parts=[types.Part(text=message or "Image not available.")])]
            else:
                contents = sdk_history + [types.Content(role="user", parts=[types.Part(text=message)])]

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=MODEL_ID,
                    contents=contents,
                    config=config
                )
            )

            ai_reply = response.text.strip()
            ai_reply = clean_reply(ai_reply)

            history.append({"role": "user", "content": message or "[Image]"})
            history.append({"role": "model", "content": ai_reply})

            if len(history) > 20:
                conversation_history[user_id] = history[-20:]

            return ai_reply

        except Exception as e:
            error_str = str(e)
            if "429" in error_str and attempt < max_retries - 1:
                logger.warning(f"Rate limit - waiting {wait_seconds}s...")
                await asyncio.sleep(wait_seconds)
                wait_seconds *= 2
                continue

            logger.error(f"AI Error: {e}")
            return "Abhi technical issue hai, thodi der baad try karo!"

    return "Server busy hai, baad mein try karo!"


def set_history(user_id, history):
    conversation_history[user_id] = history


def get_history(user_id):
    return conversation_history.get(user_id, [])