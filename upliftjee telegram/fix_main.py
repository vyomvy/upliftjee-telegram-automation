with open('/root/upliftjee/main.py', 'r') as f:
    content = f.read()

# 1. Update imports — sheets functions
old_import = """from sheets import (
    save_student, is_existing_user,
    update_member_status, get_daily_summary, load_history
)"""
new_import = """from sheets import (
    save_student, is_existing_user,
    update_member_status, get_daily_summary, load_history,
    get_preferred_language, get_first_dm_sent
)"""
content = content.replace(old_import, new_import)

# 2. Add in-memory caches near message_queue declaration
old_cache = "# ─── Message queue"
new_cache = """# ─── Language + First DM cache (in-memory, avoids repeated Sheets calls) ───
user_language = {}      # user_id -> "English" / "Hinglish"
dm_sent_cache = {}      # user_id -> True/False

# ─── Message queue"""
content = content.replace(old_cache, new_cache, 1)

# 3. Replace the whole message_handler logic to add language + carousel handling
old_handler = '''async def message_handler(client, message: Message):
    try:
        user = message.from_user
        if not user or user.is_bot:
            return

        user_id = user.id
        name = user.first_name or "Student"
        username = user.username or ""
        text = message.text or message.caption or ""

        image = None
        if message.photo:
            try:
                photo = await client.download_media(message.photo, in_memory=True)
                image = photo
            except Exception as e:
                logger.warning(f"⚠️ Photo download fail: {e}")
                image = None
                if not text:
                    await message.reply("Image nahi mili — shayad delete ho gayi. Dobara bhejein ya apna sawaal text mein likhein. 🙏")
                    return

        if not text and not image:
            await message.reply(NO_CONTENT_MSG)
            return

        logger.info(f"📩 Message aaya — {name}: {text[:50] if text else '[Image]'}")

        loop = asyncio.get_running_loop()
        if user_id not in conversation_history:
            old_history = await loop.run_in_executor(None, load_history, user_id)
            if old_history:
                conversation_history[user_id] = old_history
                logger.info(f"📂 History restore ki — {name} ({len(old_history)} msgs)")
            else:
                conversation_history[user_id] = []

        # ─── Group membership check ───
        try:
            member = await client.get_chat_member(GROUP_USERNAME, user_id)
            is_member = member.status.value in ["member", "administrator", "creator"]
        except Exception:
            is_member = False

        ai_reply = await get_ai_response(user_id, text, image)

        # ─── Group mein nahi hai toh dono links do ───
        if not is_member:
            if user_id not in invite_sent:
                ai_reply += f"\\n\\n{GROUP_INVITE}"
                invite_sent[user_id] = datetime.now()
                asyncio.create_task(send_join_reminder(client, user_id))

        await message.reply(ai_reply)

        history = get_history(user_id)
        await loop.run_in_executor(
            None,
            lambda: save_student(
                user_id=user_id,
                name=name,
                username=username,
                message=text[:200] if text else "[Image]",
                score=0,
                member_status="Member" if is_member else "Outside",
                history=history
            )
        )

        logger.info(f"✅ Reply bheja — {name}")

    except Exception as e:'''

new_handler = '''async def message_handler(client, message: Message):
    try:
        user = message.from_user
        if not user or user.is_bot:
            return

        user_id = user.id
        name = user.first_name or "Student"
        username = user.username or ""
        text = message.text or message.caption or ""

        image = None
        if message.photo:
            try:
                photo = await client.download_media(message.photo, in_memory=True)
                image = photo
            except Exception as e:
                logger.warning(f"⚠️ Photo download fail: {e}")
                image = None
                if not text:
                    await message.reply("Image nahi mili — shayad delete ho gayi. Dobara bhejein ya apna sawaal text mein likhein. 🙏")
                    return

        if not text and not image:
            await message.reply(NO_CONTENT_MSG)
            return

        logger.info(f"📩 Message aaya — {name}: {text[:50] if text else '[Image]'}")

        loop = asyncio.get_running_loop()
        is_first_message = user_id not in conversation_history

        if is_first_message:
            old_history = await loop.run_in_executor(None, load_history, user_id)
            if old_history:
                conversation_history[user_id] = old_history
                logger.info(f"📂 History restore ki — {name} ({len(old_history)} msgs)")
            else:
                conversation_history[user_id] = []

        # ─── Language preference load karo (cache se ya sheet se) ───
        if user_id not in user_language:
            saved_lang = await loop.run_in_executor(None, get_preferred_language, user_id)
            user_language[user_id] = saved_lang  # None agar set nahi hai

        # ─── First DM / Carousel status load karo ───
        if user_id not in dm_sent_cache:
            sheet_dm_status = await loop.run_in_executor(None, get_first_dm_sent, user_id)
            # None matlab user sheet mein hi nahi hai (bilkul naya)
            # False matlab sheet mein hai but carousel nahi bheja gaya
            dm_sent_cache[user_id] = sheet_dm_status

        # ─── Group membership check ───
        try:
            member = await client.get_chat_member(GROUP_USERNAME, user_id)
            is_member = member.status.value in ["member", "administrator", "creator"]
        except Exception:
            is_member = False

        ai_reply = await get_ai_response(user_id, text, image)

        # ─── Agar language set nahi hai — pehli baar pooch lo (reply ke saath) ───
        if not user_language.get(user_id):
            ai_reply += "\\n\\n🌐 Aap English mein baat karna chahte ho ya Hinglish mein? (Reply: English / Hinglish)"
            user_language[user_id] = "PENDING"  # taaki dobara na pooche jab tak student jawab na de

        elif text and text.strip().lower() in ["english", "hinglish"]:
            user_language[user_id] = text.strip().capitalize()

        # ─── Group mein nahi hai toh dono links do ───
        if not is_member:
            if user_id not in invite_sent:
                ai_reply += f"\\n\\n{GROUP_INVITE}"
                invite_sent[user_id] = datetime.now()
                asyncio.create_task(send_join_reminder(client, user_id))

        await message.reply(ai_reply)

        # ─── First DM hai aur carousel nahi bheja — ab bhejo (AI reply ke baad) ───
        needs_carousel = dm_sent_cache.get(user_id) in [None, False]
        if needs_carousel:
            asyncio.create_task(send_welcome(user_id, name))
            dm_sent_cache[user_id] = True

        history = get_history(user_id)
        lang_to_save = user_language.get(user_id)
        if lang_to_save == "PENDING":
            lang_to_save = None

        await loop.run_in_executor(
            None,
            lambda: save_student(
                user_id=user_id,
                name=name,
                username=username,
                message=text[:200] if text else "[Image]",
                score=0,
                member_status="Member" if is_member else "Outside",
                history=history,
                preferred_language=lang_to_save,
                first_dm_sent="YES" if needs_carousel else None
            )
        )

        logger.info(f"✅ Reply bheja — {name}")

    except Exception as e:'''

content = content.replace(old_handler, new_handler)

with open('/root/upliftjee/main.py', 'w') as f:
    f.write(content)

print("main.py updated!")
