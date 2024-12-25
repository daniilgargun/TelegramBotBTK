from datetime import datetime
from typing import List, Dict
from aiogram import Bot
from bot.config import config, logger
from bot.services.database import Database
from bot.middlewares.schedule_formatter import ScheduleFormatter

class NotificationManager:
    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()
        self.formatter = ScheduleFormatter()

    async def check_and_send_notifications(self):
        """Проверка новых дней в расписании и отправка уведомлений"""
        try:
            # Получаем текущее расписание
            schedule_data = await self.db.get_schedule()
            if not schedule_data:
                return

            # Получаем последнюю проверенную дату
            last_checked_dates = await self.db.get_last_checked_dates()
            
            # Находим новые дни
            new_dates = set(schedule_data.keys()) - set(last_checked_dates)
            if not new_dates:
                return

            # Получаем пользователей с включенными уведомлениями
            users = await self.db.get_users_with_notifications()
            if not users:
                return

            # Отправляем уведомления
            for user in users:
                try:
                    user_schedule = {}
                    for date in new_dates:
                        if user['role'] == 'Студент':
                            group = user.get('selected_group')
                            if group and group in schedule_data[date]:
                                user_schedule[date] = schedule_data[date][group]
                        else:  # Преподаватель
                            teacher = user.get('selected_teacher')
                            if teacher:
                                lessons = []
                                for group_schedule in schedule_data[date].values():
                                    for lesson in group_schedule:
                                        if lesson.get('teacher') == teacher:
                                            lessons.append(lesson)
                                if lessons:
                                    user_schedule[date] = lessons

                    if user_schedule:
                        # Форматируем расписание для каждого нового дня
                        for date in user_schedule:
                            formatted_schedule = self.formatter.format_schedule(
                                user_schedule[date],
                                date,
                                user
                            )
                            await self.bot.send_message(
                                user['user_id'],
                                f"🔔 Доступно новое расписание!\n\n{formatted_schedule}",
                                parse_mode="Markdown"
                            )
                            logger.info(f"Уведомление отправлено пользователю {user['user_id']}")

                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления пользователю {user['user_id']}: {e}")
                    continue

            # Обновляем последние проверенные даты
            await self.db.update_last_checked_dates(list(schedule_data.keys()))
            
        except Exception as e:
            logger.error(f"Ошибка при проверке и отправке уведомлений: {e}") 