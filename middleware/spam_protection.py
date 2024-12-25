from aiogram import BaseMiddleware
from aiogram.types import Message
from cachetools import TTLCache
from bot.config import logger, config
import logging
from datetime import datetime

class SpamProtection(BaseMiddleware):
    def __init__(self):
        self.cache = TTLCache(maxsize=10000, ttl=60.0)
        self.message_limit = 20  # Максимум сообщений в минуту
        self.warning_count = 5   # Количество предупреждений до бана
        self.banned_users = set()
        
    async def __call__(self, handler, event: Message, data):
        user_id = event.from_user.id
        
        # Пропускаем админов
        if user_id == config.admin_id:
            return await handler(event, data)
            
        # Проверяем бан
        if user_id in self.banned_users:
            return
            
        # Получаем счетчик сообщений
        user_data = self.cache.get(user_id, {"count": 0, "warnings": 0})
        user_data["count"] += 1
        
        if user_data["count"] > self.message_limit:
            user_data["warnings"] += 1
            if user_data["warnings"] >= self.warning_count:
                self.banned_users.add(user_id)
                logger.warning(f"User {user_id} banned for spam")
                await event.answer("🚫 Вы заблокированы за спам")
                return
            
            logger.warning(f"Spam warning for user {user_id}")
            await event.answer(f"⚠️ Предупреждение: слишком много сообщений ({user_data['warnings']}/{self.warning_count})")
            return
            
        self.cache[user_id] = user_data
        return await handler(event, data) 

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)
        
        # Файловый handler для безопасности
        security_handler = logging.FileHandler('security.log')
        security_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        )
        self.logger.addHandler(security_handler)
        
    def log_access(self, user_id: int, action: str, status: bool):
        """Логирование попыток доступа"""
        self.logger.info(
            f"Access attempt: user={user_id}, action={action}, "
            f"status={'success' if status else 'denied'}"
        )
        
    def log_suspicious(self, user_id: int, reason: str):
        """Логирование подозрительной активности"""
        self.logger.warning(
            f"Suspicious activity: user={user_id}, reason={reason}"
        )
        
    def log_security_event(self, event_type: str, details: dict):
        """Логирование событий безопасности"""
        self.logger.info(
            f"Security event: type={event_type}, details={details}"
        )

security_logger = SecurityLogger()