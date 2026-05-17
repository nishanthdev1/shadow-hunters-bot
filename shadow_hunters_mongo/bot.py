"""
Shadow Hunters — MongoDB Version
No PostgreSQL. No Redis. Just MongoDB Atlas + aiogram.
"""

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
import sys

import config
from database.db import connect_db, close_db
from handlers.handlers import router as main_router
from admin.admin_handlers import router as admin_router


# ─── LOGGING ──────────────────────────────────────────────────────────────────

logger.remove()
logger.add(sys.stdout,
    format="<green>{time:HH:mm:ss}</green> | <level>{level}</level> | {message}",
    level="INFO"
)


# ─── MAIN ─────────────────────────────────────────────────────────────────────

async def main():
    logger.info("⚫ Shadow Hunters starting...")

    # Connect MongoDB
    await connect_db()

    # Bot setup
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(admin_router)
    dp.include_router(main_router)

    me = await bot.get_me()
    logger.info(f"✅ Bot started: @{me.username}")
    logger.info(f"🛡️ Admins: {config.ADMIN_IDS}")
    logger.info("🌀 Gates are open!")

    try:
        await dp.start_polling(bot, drop_pending_updates=True)
    finally:
        await close_db()
        await bot.session.close()
        logger.info("🛑 Bot stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Stopped.")
