import locale
import logging
from datetime import datetime
from typing import List, Dict, Any
from bot.config import format_date

logger = logging.getLogger(__name__)

try:
    locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'ru_RU')
    except locale.Error:
        logger.warning("Не удалось установить русскую локаль")

def _translate_day(day: str) -> str:
    """Перевод дня недели с русского на английский и обратно"""
    ru_to_en = {
        'понедельник': 'monday',
        'вторник': 'tuesday', 
        'среда': 'wednesday',
        'четверг': 'thursday',
        'пятница': 'friday',
        'суббота': 'saturday',
        'воскресенье': 'sunday'
    }
    
    en_to_ru = {
        'monday': 'понедельник',
        'tuesday': 'вторник',
        'wednesday': 'среда', 
        'thursday': 'четверг',
        'friday': 'пятница',
        'saturday': 'суббота',
        'sunday': 'воскресенье'
    }

    day = day.lower()
    if day in ru_to_en:
        return ru_to_en[day]
    elif day in en_to_ru:
        return en_to_ru[day]
    return day

def format_date(date_str: str) -> str:
    """Форматирование даты в формат '23-дек (понедельник)'"""
    try:
        # Парсим дату формата "23-дек"
        if '-' in date_str:
            day, month = date_str.split('-')
        else:
            return date_str
            
        # Создаем объект datetime
        current_year = datetime.now().year
        date_obj = datetime.strptime(f"{day}-{month}-{current_year}", "%d-%b-%Y")
        
        # Получаем день недели
        weekday_ru = {
            'Monday': 'понедельник',
            'Tuesday': 'вторник',
            'Wednesday': 'среда',
            'Thursday': 'четверг',
            'Friday': 'пятница',
            'Saturday': 'суббота',
            'Sunday': 'воскресенье'
        }
        weekday = weekday_ru[date_obj.strftime('%A')]
        
        # Форматируем дату в нужный формат
        return f"{day}-{month} ({weekday})"
    except Exception as e:
        logger.error(f"Ошибка форматирования даты: {e}")
        return date_str

class ScheduleFormatter:
    @staticmethod
    def format_schedule(schedule_data: str | List[Dict] | None, day: str, user_data: dict) -> str:
        """Форматирование расписания на день"""
        # Если получили None - расписание не загружено
        if schedule_data is None:
            return f"❌ Расписание на {day.lower()} не загружено"

        # Если получили строку (сообщение об ошибке), возвращаем её
        if isinstance(schedule_data, str):
            return schedule_data

        # Если расписание пустое для выбранной группы/преподавателя, но есть для других
        if not schedule_data and isinstance(schedule_data, list):
            if user_data.get('role') == 'Студент':
                return f"📅 {day.capitalize()}\n✨═════════════════════✨\n\nУ группы {user_data.get('selected_group')} в этот день нет занятий"
            else:
                return f"📅 {day.capitalize()}\n✨═════════════════════✨\n\nУ преподавателя {user_data.get('selected_teacher')} в этот день нет занятий"

        # Формируем заголовок
        header = "🎓 Расписание "
        if user_data.get('role') == 'Студент':
            header += f"группы {user_data.get('selected_group')}\n\n"
        else:
            header += f"преподавателя {user_data.get('selected_teacher')}\n\n"

        # Форматируем дату
        formatted_date = f"📅 {format_date(day)}"

        response = [
            header,
            formatted_date,
            "❄️═════════════════════❄️\n"
        ]

        # Группируем пары
        grouped_lessons = []
        current_group = None
        
        for lesson in sorted(schedule_data, key=lambda x: int(x['number'])):
            if current_group and ScheduleFormatter._can_group_lessons(current_group[-1], lesson):
                current_group.append(lesson)
            else:
                if current_group:
                    grouped_lessons.append(current_group)
                current_group = [lesson]
        
        if current_group:
            grouped_lessons.append(current_group)

        # Форматируем каждую группу пар
        for group in grouped_lessons:
            if len(group) > 1:
                numbers = f"{group[0]['number']}-{group[-1]['number']}"
            else:
                numbers = group[0]['number']

            lesson_block = [
                f"🕐 {numbers} пара",
                f"📚 {group[0]['discipline']}"
            ]

            if user_data.get('role') == 'Студент':
                lesson_block.append(f"🎅 {group[0]['teacher']}")
            else:
                # Для преподавателей показываем группу
                groups = set()
                for lesson in group:
                    if lesson.get('group'):
                        groups.add(lesson['group'])
                if groups:
                    lesson_block.append(f"👥 Группа: {', '.join(sorted(groups))}")

            lesson_block.append(f"⛄️ Кабинет: {group[0]['classroom']}")

            if group[0].get('subgroup') and group[0]['subgroup'] != '0':
                lesson_block.append(f"👥 Подгруппа {group[0]['subgroup']}")

            response.extend(lesson_block)
            response.append("")  # Пустая строка между парами

        return "\n".join(response)

    @staticmethod
    def _can_group_lessons(lesson1: dict, lesson2: dict) -> bool:
        """Проверка возможности группировки пар"""
        return (
            lesson1['discipline'] == lesson2['discipline'] and
            lesson1['teacher'] == lesson2['teacher'] and
            lesson1['classroom'] == lesson2['classroom'] and
            lesson1.get('subgroup', '0') == lesson2.get('subgroup', '0') and
            int(lesson2['number']) == int(lesson1['number']) + 1
        )

    @staticmethod
    def format_full_schedule(schedule_data: dict | None, user_data: dict) -> str:
        """Форматирование полного расписания на неделю"""
        # Если расписание не загружено
        if schedule_data is None:
            return "❌ Расписание не загружено"

        # Если расписание пустое для всех
        if not schedule_data:
            return "❄📅 Расписание\n✨═════════════════════✨\n\nНа этой неделе нет расписания"

        # Формируем заголовок
        header = "🎓 Расписание "
        if user_data.get('role') == 'Студент':
            header += f"группы {user_data.get('selected_group')}\n\n"
        else:
            header += f"преподавателя {user_data.get('selected_teacher')}\n\n"

        formatted_days = [header]
        
        # Сортируем дни по дате
        def parse_date(date_str):
            try:
                if '-' in date_str:
                    day, month = date_str.split('-')
                    return datetime.strptime(f"{day}-{month}-{datetime.now().year}", "%d-%b-%Y")
                return datetime.max
            except:
                return datetime.max

        sorted_dates = sorted(schedule_data.keys(), key=parse_date)

        for date in sorted_dates:
            day_schedule = schedule_data[date]
            if not day_schedule:
                if user_data.get('role') == 'Студент':
                    formatted_days.append(
                        f"📅 {format_date(date)}\n"
                        f"✨═════════════════════✨\n\n"
                        f"У группы {user_data.get('selected_group')} в этот день нет занятий"
                    )
                else:
                    formatted_days.append(
                        f"📅 {format_date(date)}\n"
                        f"✨═════════════════════✨\n\n"
                        f"У преподавателя {user_data.get('selected_teacher')} в этот день нет занятий"
                    )
                continue

            # Форматируем дату
            formatted_date = f"📅 {format_date(date)}"

            day_block = [
                formatted_date,
                "❄️═════════════════════❄️\n"
            ]

            # Группируем пары
            grouped_lessons = []
            current_group = None
            sorted_schedule = sorted(day_schedule, key=lambda x: int(x['number']))

            for lesson in sorted_schedule:
                if current_group and ScheduleFormatter._can_group_lessons(current_group[-1], lesson):
                    current_group.append(lesson)
                else:
                    if current_group:
                        grouped_lessons.append(current_group)
                    current_group = [lesson]

            if current_group:
                grouped_lessons.append(current_group)

            # Форматируем каждую группу пар
            for group in grouped_lessons:
                if len(group) > 1:
                    numbers = f"{group[0]['number']}-{group[-1]['number']}"
                else:
                    numbers = group[0]['number']

                lesson_block = [
                    f"🕐 {numbers} пара",
                    f"📚 {group[0]['discipline']}"
                ]

                if user_data.get('role') == 'Студент':
                    lesson_block.append(f"🎅 {group[0]['teacher']}")
                else:
                    # Для преподавателей показываем группу
                    groups = set()
                    for lesson in group:
                        if lesson.get('group'):
                            groups.add(lesson['group'])
                    if groups:
                        lesson_block.append(f"👥 Группа: {', '.join(sorted(groups))}")

                lesson_block.append(f"⛄️ Кабинет: {group[0]['classroom']}")

                if group[0].get('subgroup') and group[0]['subgroup'] != '0':
                    lesson_block.append(f"👥 Подгруппа {group[0]['subgroup']}")

                day_block.extend(lesson_block)
                day_block.append("")  # Пустая строка между парами

            formatted_days.append("\n".join(day_block))

        return "\n\n".join(formatted_days) 