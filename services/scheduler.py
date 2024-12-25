import locale
from datetime import datetime
import asyncio
import aioschedule as schedule
from bot.services.parser import ScheduleParser
from bot.services.database import Database
from bot.config import logger
from bot.services.notifications import NotificationManager

try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_ALL, 'ru_RU')
    except locale.Error:
        locale.setlocale(locale.LC_ALL, '')

class ScheduleUpdater:
    def __init__(self):
        self.parser = ScheduleParser()
        self.db = Database()
        self.last_update = None
        self.update_count = 0
        self.error_count = 0

    async def get_stats(self):
        return {
            'last_update': self.last_update,
            'update_count': self.update_count,
            'error_count': self.error_count
        }

    async def update_schedule(self):
        """Обновление расписания"""
        try:
            if datetime.now().weekday() == 6:
                logger.info("Воскресенье: обновление расписания пропущено")
                return

            current_hour = datetime.now().hour
            if not (7 <= current_hour < 19):
                logger.info(f"Время {current_hour}:00 вне диапазона обновления (7:00-19:00)")
                return

            logger.info("Начало планового обновления расписания")
            schedule_data, groups_list, teachers_list, error = await self.parser.parse_schedule()

            if error:
                logger.error(f"Ошибка при плановом обновлении: {error}")
                self.error_count += 1
                return

            await self.db.update_schedule(schedule_data)
            await self.db.update_cache_time()
            
            self.last_update = datetime.now()
            self.update_count += 1
            
            logger.info(f"Плановое обновление завершено. Групп: {len(groups_list)}, Преподавателей: {len(teachers_list)}")

        except Exception as e:
            logger.error(f"Ошибка при плановом обновлении расписания: {e}")
            self.error_count += 1

async def start_scheduler(bot):
    """Запуск планировщика"""
    updater = ScheduleUpdater()
    
    # Планируем обновление каждые 5 минут
    schedule.every(5).minutes.do(updater.update_schedule)
    
    logger.info("Планировщик обновления расписания запущен")
    
    notification_manager = NotificationManager(bot)
    
    # Добавляем задачу проверки новых дней в расписании
    schedule.every(5).minutes.do(notification_manager.check_and_send_notifications)
    
    while True:
        await schedule.run_pending()
        await asyncio.sleep(1)