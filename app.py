import asyncio
import logging
import os
import signal
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiohttp import web

from config import BOT_TOKEN, PORT
from handlers import common, transactions, stats, events_handler
from services.exchange_rates import refresh_rates_loop
from services.event_checker import check_events_loop

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Флаг для остановки фоновых задач
shutdown_flag = False

def handle_signal(signum, frame):
    global shutdown_flag
    logger.info(f"Получен сигнал {signum}, завершаем работу...")
    shutdown_flag = True

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

async def main():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Устанавливаем ссылку на бота для использования в хендлерах
    common.set_bot_ref(bot)

    # Register routers
    dp.include_router(common.router)
    dp.include_router(transactions.router)
    dp.include_router(stats.router)
    dp.include_router(events_handler.router)

    # Background tasks
    server_task = asyncio.create_task(start_fake_server())
    rates_task = asyncio.create_task(refresh_rates_loop())
    events_check_task = asyncio.create_task(check_events_loop(bot))
    
    logger.info("Starting bot polling...")
    
    try:
        await dp.start_polling(bot)
    finally:
        global shutdown_flag
        shutdown_flag = True
        # Отменяем фоновые задачи
        for task in [server_task, rates_task, events_check_task]:
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        await bot.session.close()
        logger.info("Бот остановлен, ресурсы освобождены.")

if __name__ == "__main__":
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Бот остановлен пользователем.")