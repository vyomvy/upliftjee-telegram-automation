with open('/root/upliftjee/main.py', 'r') as f:
    content = f.read()

old = '''        # ─── Agar language set nahi hai — pehli baar pooch lo (reply ke saath) ───
        if not user_language.get(user_id):
            ai_reply += "\\n\\n🌐 Aap English mein baat karna chahte ho ya Hinglish mein? (Reply: English / Hinglish)"
            user_language[user_id] = "PENDING"  # taaki dobara na pooche jab tak student jawab na de

        elif text and text.strip().lower() in ["english", "hinglish"]:
            user_language[user_id] = text.strip().capitalize()'''

new = '''        # ─── Language detect karo (AI system prompt khud poochta hai, hum sirf track karte hain) ───
        if not user_language.get(user_id):
            user_language[user_id] = "PENDING"

        if text and text.strip().lower() in ["english", "hinglish"]:
            user_language[user_id] = text.strip().capitalize()'''

content = content.replace(old, new)

with open('/root/upliftjee/main.py', 'w') as f:
    f.write(content)

print("Fixed!")
