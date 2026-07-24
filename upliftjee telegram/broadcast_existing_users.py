import asyncio
import random
import logging
from pyrogram import Client
from config import API_ID, API_HASH, PHONE_NUMBER

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

IMAGES_DIR = "/root/upliftjee/images"
CAROUSEL_IMAGES = [
    "1_books.jpeg",
    "2_courses.jpeg",
    "3_jee_adv_pyq.jpeg",
    "4_jee_main_pyq.jpeg",
    "5_kota_11.jpeg",
    "6_kota_12.jpeg",
]

WELCOME_MSG = """Namaste! 👋 Om Sharma Sir ke group mein swagat hai!

📚 JEE doubt hai? — ques likho ya photo bhejo
💬 Koi bhi query? — seedha poochho
🎯 Course, Books, Kota Module Solutions, PYQ Solutions, Test Series — bas bolo, sb hai yaha!

Shuru karo! 😊"""

app = Client(
    "omsir_session",
    api_id=API_ID,
    api_hash=API_HASH,
    phone_number=PHONE_NUMBER
)


async def _do_send(user_id, name):
    import os
    from pyrogram.types import InputMediaPhoto

    media = []
    for img in CAROUSEL_IMAGES:
        path = os.path.join(IMAGES_DIR, img)
        if os.path.exists(path):
            media.append(InputMediaPhoto(media=path))

    if media:
        await app.send_media_group(user_id, media)
        await asyncio.sleep(1)

    await app.send_message(user_id, WELCOME_MSG)


async def send_carousel(user_id, name):
    try:
        # 30 second hard timeout per user — koi bhi user zyada der nahi atkayega
        await asyncio.wait_for(_do_send(user_id, name), timeout=30)
        return True

    except asyncio.TimeoutError:
        logger.warning(f"⏱️ Timeout (30s) — {name} ({user_id}) skip kar rahe hain")
        return False

    except Exception as e:
        error_str = str(e)
        if "PEER_ID_INVALID" in error_str:
            logger.info(f"⏭️ Skip — {name} ({user_id}) ne kabhi Sir ko message nahi kiya")
        elif "PEER_FLOOD" in error_str:
            logger.warning(f"🛑 PEER_FLOOD — {name} ({user_id})")
            raise
        elif "USER_IS_BLOCKED" in error_str or "INPUT_USER_DEACTIVATED" in error_str:
            logger.info(f"⏭️ Skip — {name} ({user_id}) blocked/deactivated")
        else:
            logger.warning(f"⚠️ Error — {name} ({user_id}): {e}")
        return False


async def main():
    from sheets import get_sheet

    sheet = get_sheet()
    rows = sheet.get_all_values()
    users = rows[1:]

    logger.info(f"📋 Total users to process: {len(users)}")

    sent_count = 0
    fail_count = 0

    async with app:
        for i, row in enumerate(users, start=1):
            if not row or len(row) < 3 or not row[2]:
                continue

            user_id = int(row[2])
            name = row[1] if len(row) > 1 else "Student"

            already_sent = len(row) > 11 and row[11] == "YES"
            if already_sent:
                logger.info(f"⏭️ ({i}/{len(users)}) Already sent — {name}")
                continue

            logger.info(f"📤 ({i}/{len(users)}) Sending to {name} ({user_id})...")

            try:
                success = await send_carousel(user_id, name)
            except Exception:
                logger.error("🛑 PEER_FLOOD hit — pausing for 1 hour")
                await asyncio.sleep(3600)
                try:
                    success = await send_carousel(user_id, name)
                except Exception:
                    success = False

            if success:
                row_num = i + 1
                sheet.update_cell(row_num, 12, "YES")
                sent_count += 1
                logger.info(f"✅ Sent — {name}")
            else:
                fail_count += 1

            delay = random.uniform(8, 15)
            await asyncio.sleep(delay)

    logger.info(f"🎉 Broadcast complete! Sent: {sent_count}, Skipped/Failed: {fail_count}")


if __name__ == "__main__":
    asyncio.run(main())
