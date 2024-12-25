from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
import re
from datetime import datetime
import pytz
from random import choice
from bot.services.database import Database
from bot.config import logger
import asyncio

router = Router()

def get_current_year():
    """Получение текущего года по МСК"""
    msk_tz = pytz.timezone('Europe/Moscow')
    return datetime.now(msk_tz).year

def get_next_year():
    """Получение следующего года по МСК"""
    return get_current_year() + 1

# Паттерны для распознавания новогодних поздравлений
def get_new_year_patterns():
    next_year = get_next_year()
    patterns = [
        fr'с[\s]*новым[\s]*годом[\s]*{next_year}',
        fr'с[\s]*новым[\s]*{next_year}[\s]*годом',
        fr'happy[\s]*new[\s]*year[\s]*{next_year}',
        fr'с[\s]*наступающим[\s]*{next_year}',
        r'с[\s]*новым[\s]*годом',
        r'happy[\s]*new[\s]*year',
        r'с[\s]*наступающим',
        r'новым[\s]*годом',
        r'с[\s]*нг',
        r'с[\s]*нг[\s]*\d{4}',
        fr'с[\s]*нг[\s]*{next_year}',
        r'hny',
        r'hny[\s]*\d{4}',
        fr'hny[\s]*{next_year}',
        r'с[\s]*наступающим[\s]*нг',
        r'с[\s]*праздником',
        r'поздравляю[\s]*с[\s]*нг',
        r'поздравляю[\s]*с[\s]*новым[\s]*годом',
        fr'поздравляю[\s]*с[\s]*{next_year}',
        r'ny',
        r'new[\s]*year',
        r'наступающим',
        r'праздником'
    ]
    return [re.compile(pattern, re.IGNORECASE) for pattern in patterns]

def get_new_year_responses():
    """Праздничные ответы с автоматическим годом"""
    next_year = get_next_year()
    return [
        f"🎄 С Новым {next_year} Годом! Пусть этот год принесет много счастья и успехов! ⭐",
        f"🎅 Спасибо за поздравление! И вас с Новым {next_year} Годом! Желаю исполнения всех желаний! 🎁",
        f"❄️ С Новым {next_year} Годом! Пусть он будет полон чудес и радостных моментов! 🌟",
        f"🎊 И вас с Новым {next_year} Годом! Счастья, здоровья и всего самого наилучшего! 🎄",
        f"✨ Спасибо! С Новым {next_year} Годом! Пусть этот год будет особенным! 🎅",
        f"🌟 С наступающим {next_year} годом! Пусть каждый день будет наполнен радостью и вдохновением! 🎊",
        f"🎁 Взаимно поздравляю с Новым {next_year} Годом! Желаю море позитива и исполнения заветных желаний! ✨",
        f"⭐ С Новым {next_year} Годом! Пусть этот год подарит множество поводов для улыбок и счастья! 🎄",
        f"🎈 И вас с праздником! Пусть {next_year} год станет временем великих свершений! 🌟",
        f"🎆 С Новым {next_year} Годом! Желаю, чтобы этот год был наполнен яркими и незабываемыми моментами! 🎊"
    ]

@router.message(lambda message: any(pattern.search(message.text.lower()) for pattern in get_new_year_patterns()) if message.text else False)
async def handle_new_year_greetings(message: Message):
    """Обработка новогодних поздравлений"""
    response = choice(get_new_year_responses())
    await message.reply(response)

async def send_new_year_greetings(bot):
    """Отправка новогодних поздравлений с отсчетом"""
    msk_tz = pytz.timezone('Europe/Moscow')
    now = datetime.now(msk_tz)
    
    if now.month == 12 and now.day == 31 and now.hour == 23 and now.minute == 50:
        next_year = get_next_year()
        greeting = (
            f"🎄 С Новым {next_year} Годом! 🎊\n\n"
            "Здравствуйте! Ваш бот по расписанию БТК здесь, чтобы поздравить вас с наступлением Нового Года! 🎅\n"
            "Пусть новый год будет полон точности и пунктуальности, как идеально составленное расписание! ✨\n"
            "Желаю вам исполнения всех желаний, особенно тех, что связаны с успешной сдачей сессий и получением автоматов! 🌟\n\n"
            "Ваш помощник по расписанию БТK"
        )
        db = Database()
        users = await db.get_all_users()
        
        tasks = []
        for user in users:
            try:
                user_id = int(user['user_id'])
                tasks.append(bot.send_message(chat_id=user_id, text=greeting))
                logger.info(f"Подготовлено новогоднее поздравление пользователю {user_id}")
            except Exception as e:
                logger.error(f"Ошибка при подготовке поздравления пользователю {user_id}: {e}")
        
        # Отправляем все сообщения одновременно
        await asyncio.gather(*tasks)

# # Можно добавить и другие праздничные обработчики
# @router.message(Command("holiday"))
# async def show_holiday_commands(message: Message):
#     """Показать список праздничных команд"""
#     commands = (
#         "🎄 Праздничные команды:\n\n"
#         "• Поздравьте бота с Новым Годом\n"
#         "• /holiday - показать это сообщение\n"
#     )
#     await message.answer(commands)
    
# @router.message(Command("test_countdown"))
# async def test_new_year_countdown(message: Message):
#     """Тестовый запуск новогоднего отсчёта для всех пользователей"""
#     next_year = get_next_year()
#     greeting = (
#         f"🎄 С Новым {next_year} Годом! 🎊\n\n"
#         "Здравствуйте! Ваш бот по расписанию БТК здесь, чтобы поздравить вас с наступлением Нового Года! 🎅\n"
#         "Пусть новый год будет полон точности и пунктуальности, как идеально составленное расписание! ✨\n"
#         "Желаю вам исполнения всех желаний, особенно тех, что связаны с успешной сдачей сессий и получением автоматов! 🌟\n\n"
#         "С юмором и наилучшими пожеланиями,\n"
#         "Ваш помощник по расписанию БТK"
#     )

#     db = Database()
#     users = await db.get_all_users()
    
#     tasks = []
#     for user in users:
#         try:
#             user_id = int(user['user_id'])
#             tasks.append(message.bot.send_message(chat_id=user_id, text=greeting))
#             logger.info(f"Подготовлено тестовое новогоднее поздравление пользователю {user_id}")
#         except Exception as e:
#             logger.error(f"Ошибка при подготовке тестового поздравления пользователю {user_id}: {e}")
#             continue
    
#     # Отправляем все сообщения одновременно        
#     await asyncio.gather(*tasks)
#     await message.answer("✅ Тестовая рассылка новогодних поздравлений завершена")
