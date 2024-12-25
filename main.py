import asyncio
import signal
import sys
from aiogram import Bot, Dispatcher
from bot.config import config, logger
from bot.handlers import main_router
from bot.services.scheduler import start_scheduler
from bot.middleware.rate_limit import RateLimitMiddleware
from bot.middleware.spam_protection import SpamProtection
from bot.middleware.performance import PerformanceMiddleware
from bot.services.monitoring import monitor
from contextlib import asynccontextmanager

class BotApp:
    def __init__(self):
        self.bot = Bot(token=config.token)
        self.dp = Dispatcher()
        self.tasks = []
        self.is_running = True

    async def setup(self):
        """Настройка бота и middleware"""
        # Подключаем middleware
        self.dp.message.middleware(RateLimitMiddleware())
        self.dp.message.middleware(SpamProtection())
        self.dp.message.middleware(PerformanceMiddleware())
        
        # Регистрация роутеров
        self.dp.include_router(main_router)

    async def start(self):
        """Запуск всех сервисов бота"""
        await self.setup()
        
        # Запускаем фоновые задачи
        self.tasks.extend([
            asyncio.create_task(self.metrics_collector()),
            asyncio.create_task(start_scheduler(self.bot))
        ])
        
        logger.info("Bot services started")

    async def stop(self):
        """Корректное завершение работы бота"""
        logger.info("Shutting down bot...")
        self.is_running = False
        
        # Отменяем все фоновые задачи
        for task in self.tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        # Закрываем сессию бота
        await self.bot.session.close()
        logger.info("Bot shutdown complete")

    async def metrics_collector(self):
        """Периодический сбор метрик"""
        while self.is_running:
            try:
                await monitor.collect_metrics()
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in metrics collector: {e}")
                await asyncio.sleep(5)

@asynccontextmanager
async def bot_app():
    """Контекстный менеджер для управления жизненным циклом бота"""
    app = BotApp()
    
    def signal_handler(signum, frame):
        """Обработчик сигналов для корректного завершения"""
        logger.info(f"Received signal {signum}")
        asyncio.create_task(app.stop())
    
    # Регистрируем обработчики сигналов
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, signal_handler)
    
    try:
        await app.start()
        yield app
    finally:
        await app.stop()

async def main():
    """Основная функция запуска бота"""
    async with bot_app() as app:
        try:
            logger.info("Starting bot polling...")
            await app.dp.start_polling(app.bot)
        except Exception as e:
            logger.error(f"Critical error: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by keyboard interrupt!")
    except Exception as e:
        logger.error(f"Fatal error: {e}")