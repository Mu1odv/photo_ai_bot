import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# O'zingizning fayllaringizdan importlar
from config import BOT_TOKEN
from handlers import user, admin

async def main():
    # 1. DATABASE BILAN ISHLASH (SQLite sinxron ulanish)
    try:
        print("Bazani ishga tushirmoqda...")
        # Database birinchi ishga tushirilganda create_tables chaqiriladi
        # Shuning uchun db obyekti butun bo'lib turibdi
        print("✅ Ma'lumotlar bazasi tayyor!")
    except Exception as e:
        print(f"❌ Bazada xatolik: {e}")
        return

    # 2. DISPATCHER OBYEKTINI YARATAMIZ
    dp = Dispatcher()

    # 3. BOT OBYEKTI
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # 4. ROUTERLARNI ULASH (Tartibga e'tibor bering: admin birinchi)
    dp.include_router(admin.router)
    dp.include_router(user.router)

    # 5. LOGLARNI SOZLASH
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print("🚀 Bot ishga tushdi!")

    # Botni ishga tushiramiz
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot to'xtatildi!")