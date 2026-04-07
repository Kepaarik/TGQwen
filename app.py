import asyncio
import logging
import os
import random
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web
import aiohttp

from config import BOT_TOKEN, PORT
from handlers import common, transactions, stats, events_handler
from services.exchange_rates import refresh_rates_loop

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL вашего сервиса на Render (задаётся через переменную окружения RENDER_URL)
RENDER_URL = os.getenv("RENDER_URL", "")

async def handle_request(request):
    return web.Response(text="Bot is running")

async def start_fake_server():
    app = web.Application()
    app.router.add_get('/', handle_request)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    logger.info(f"Fake server started on port {PORT}")

async def keep_alive():
    """Пингует собственный URL каждые 1-5 секунд (случайно), чтобы Render не усыплял сервис."""
    if not RENDER_URL:
        logger.warning("RENDER_URL не задан — keep-alive отключён.")
        return
    logger.info(f"Keep-alive запущен, пингуем {RENDER_URL} каждые 1-5 сек (случайно).")
    while True:
        delay = random.uniform(1, 5)
        await asyncio.sleep(delay)
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(RENDER_URL, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    logger.info(f"Keep-alive ping: {resp.status}")
        except Exception as e:
            logger.warning(f"Keep-alive ошибка: {e}")

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Register routers
    dp.include_router(common.router)
    dp.include_router(transactions.router)
    dp.include_router(stats.router)
    dp.include_router(events_handler.router)

    # Background tasks
    asyncio.create_task(start_fake_server())
    asyncio.create_task(keep_alive())
    asyncio.create_task(refresh_rates_loop())
    
    logger.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped.")