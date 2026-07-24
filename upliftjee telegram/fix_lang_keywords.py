with open('/root/upliftjee/main.py', 'r') as f:
    content = f.read()

old = '''        # ─── Language detect karo (AI system prompt khud poochta hai, hum sirf track karte hain) ───
        if not user_language.get(user_id):
            user_language[user_id] = "PENDING"

        if text and text.strip().lower() in ["english", "hinglish"]:
            user_language[user_id] = text.strip().capitalize()'''

new = '''        # ─── Language detect karo (AI system prompt khud poochta hai, hum sirf track karte hain) ───
        if not user_language.get(user_id):
            user_language[user_id] = "PENDING"

        if user_language.get(user_id) == "PENDING" and text:
            msg_lower = text.strip().lower()
            if "hinglish" in msg_lower or "hindi" in msg_lower:
                user_language[user_id] = "Hinglish"
            elif "english" in msg_lower:
                user_language[user_id] = "English"'''

content = content.replace(old, new)

with open('/root/upliftjee/main.py', 'w') as f:
    f.write(content)

print("Fixed!")
