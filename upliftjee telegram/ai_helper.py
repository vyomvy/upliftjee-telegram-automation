from google import genai
from google.genai import types
from config import SYSTEM_PROMPT
import re
import asyncio
import logging

logger = logging.getLogger(__name__)

PROJECT_ID = "upliftjee"
LOCATION = "us-central1"

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
MODEL_ID = "gemini-2.5-flash"

conversation_history = {}

# ─── Keywords for dynamic thinking budget (original logic — untouched) ───
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
    Message type ke hisaab se thinking budget — original logic same.
    Simple → fast, Hard JEE → full thinking.
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
    AI reply se LaTeX, dollar signs, code blocks remove karo — original logic same.
    """
    text = text.replace("💪", "")

    text = re.sub(r'\$\$(.+?)\$\$', lambda m: m.group(1).strip(), text, flags=re.DOTALL)
    text = re.sub(r'\$(.+?)\$', lambda m: m.group(1).strip(), text)

    text = re.sub(r'```[\w]*\n?', '', text)
    text = re.sub(r'```', '', text)
    text = re.sub(r'`(.+?)`', lambda m: m.group(1), text)

    text = text.replace(r'\frac{', '(').replace(r'\frac', '')
    text = re.sub(r'\\frac\{(.+?)\}\{(.+?)\}', r'(\1)/(\2)', text)
    text = re.sub(r'\\sqrt\{(.+?)\}', r'sqrt(\1)', text)
    text = text.replace(r'\sqrt', 'sqrt')
    text = re.sub(r'\\int', 'integral', text)
    text = re.sub(r'\\sum', 'sum', text)
    text = re.sub(r'\\infty', 'infinity', text)
    text = re.sub(r'\\alpha', 'alpha', text)
    text = re.sub(r'\\beta', 'beta', text)
    text = re.sub(r'\\theta', 'theta', text)
    text = re.sub(r'\\pi', 'pi', text)
    text = re.sub(r'\\times', 'x', text)
    text = re.sub(r'\\cdot', '.', text)
    text = re.sub(r'\\leq', '<=', text)
    text = re.sub(r'\\geq', '>=', text)
    text = re.sub(r'\\neq', '!=', text)
    text = re.sub(r'\\pm', '+/-', text)
    text = re.sub(r'\\[a-zA-Z]+\{?', '', text)
    text = re.sub(r'\{|\}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()


async def get_ai_response(user_id, message, image=None):
    """
    AI se response lo — async version.
    Bot freeze nahi hoga — multiple students simultaneously handle hoga.
    Dynamic thinking budget + retry logic — original features intact.
    """
    if user_id not in conversation_history:
        conversation_history[user_id] = []

    history = conversation_history[user_id]

    budget = get_thinking_budget(message, image)
    logger.info(f"🧠 Thinking budget: {budget} — {'Image' if image else (message[:30] if message else '[empty]')}")

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        thinking_config=types.ThinkingConfig(
            thinking_budget=budget
        )
    )

    # History SDK format mein convert karo
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
            # Contents banao
            if image:
                try:
                    image_bytes = image.getvalue()
                    contents = sdk_history + [
                        types.Content(
                            role="user",
                            parts=[
                                types.Part(
                                    inline_data=types.Blob(
                                        mime_type="image/jpeg",
                                        data=image_bytes
                                    )
                                ),
                                types.Part(
                                    text=message if message else "Is image mein jo question hai use plain text mein samjhao."
                                )
                            ]
                        )
                    ]
                except Exception as img_err:
                    logger.warning(f"⚠️ Image process nahi hui: {img_err} — text se try kar raha hoon")
                    fallback = message if message else "Student ne ek image bheji jo ab available nahi hai. Unhe bolao dobara bhejein."
                    contents = sdk_history + [
                        types.Content(role="user", parts=[types.Part(text=fallback)])
                    ]
            else:
                contents = sdk_history + [
                    types.Content(role="user", parts=[types.Part(text=message)])
                ]

            # ✅ Gemini call — background thread mein, event loop block nahi hoga
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

            # RAM history update — last MAX_RAM_HISTORY messages rakhna
            history.append({"role": "user", "content": message or "[Image]"})
            history.append({"role": "model", "content": ai_reply})

            if len(history) > 20:
                conversation_history[user_id] = history[-20:]

            return ai_reply

        except Exception as e:
            error_str = str(e)

            if "429" in error_str and attempt < max_retries - 1:
                logger.warning(f"⏳ Rate limit (429) — {wait_seconds}s wait... (attempt {attempt + 1}/{max_retries})")
                await asyncio.sleep(wait_seconds)  # ✅ bot freeze nahi hoga during wait
                wait_seconds *= 2
                continue

            logger.error(f"❌ AI error (attempt {attempt + 1}): {e}")
            return "Abhi ek technical issue aa gaya — kuch time mein dobara bhejo!"

    logger.error(f"❌ AI error: Saare {max_retries} retries fail — user {user_id}")
    return "Abhi server busy hai — thodi der baad dobara bhejo!"


def set_history(user_id, history):
    conversation_history[user_id] = history


def get_history(user_id):
    return conversation_history.get(user_id, [])