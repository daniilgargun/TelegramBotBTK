from aiogram import Router, F
from aiogram.types import Message
from bot.keyboards.keyboards import get_admin_keyboard
from bot.config import config
from bot.config import logger
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from bot.services.database import Database
from bot.services.parser import ScheduleParser
from google.cloud import firestore
from datetime import datetime, timedelta
import psutil
import os
from bot.utils.validators import InputValidator
from bot.services.logger import security_logger
from bot.services.monitoring import monitor

db = Database()

class AdminStates(StatesGroup):
    waiting_for_broadcast_message = State()
    waiting_for_user_id = State()
    waiting_for_user_message = State()
    waiting_for_schedule_type = State()
    waiting_for_schedule_photo = State()
    
router = Router()

@router.message(F.text == "Админ-панель")
async def admin_panel(message: Message):
    if message.from_user.id != config.admin_id:
        await message.answer("⛔️ У вас нет доступа к этой команде")
        return
        
    await message.answer(
        "🛠 *Панель управления администратора*\n\n"
            "Выберите необходимое действие из меню ниже.",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(lambda c: c.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != config.admin_id:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        # Получаем статистику пользователей
        users = await db.get_all_users()
        total_users = len(users)
        
        # Считаем пользователей с уведомлениями
        notif_users = len([u for u in users if u.get('notifications', False)])

        # Считаем пользователей по ролям
        students = len([u for u in users if u.get('role') == 'student'])
        teachers = len([u for u in users if u.get('role') == 'teacher'])

        # Время работы бота
        bot_start_time = os.path.getctime(os.path.abspath(__file__))
        uptime = datetime.now() - datetime.fromtimestamp(bot_start_time)
        uptime_days = uptime.days
        uptime_hours = uptime.seconds // 3600 
        uptime_minutes = (uptime.seconds % 3600) // 60
        
        # Кэш
        cached_groups = len(await db.get_cached_groups())
        cached_teachers = len(await db.get_cached_teachers())

        stats_text = (
            "📊 *Детальная статистика бота*\n\n"
            f"⏱️ Время работы:\n"
            f"   • Дней: {uptime_days}\n"
            f"   • Часов: {uptime_hours}\n"
            f"   • Минут: {uptime_minutes}\n\n"
            f"👥 Пользователи:\n"
            f"   • Всего: {total_users}\n"
            f"   • Студентов: {students}\n"
            f"   • Преподавателей: {teachers}\n"
            f"   • С уведомлениями: {notif_users}\n\n"
            f"💾 Кэш:\n"
            f"   • Групп: {cached_groups}\n"
            f"   • Преподавателей: {cached_teachers}"
        )
        
        back_button = [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]]
        await callback.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=back_button),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при получении статистики: {e}")
        await callback.answer("❌ Произошла ошибка при получении статистики")

@router.callback_query(lambda c: c.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    if callback.from_user.id != config.admin_id:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        users = await db.get_all_users()
        
        # Подсчет статистики по группам
        group_stats = {}
        total_students = 0
        total_teachers = 0
        
        for user in users:
            role = user.get('role')
            if role == 'Студент':
                total_students += 1
                group = user.get('selected_group')
                if group:
                    group_stats[group] = group_stats.get(group, 0) + 1
            elif role == 'Преподаватель':
                total_teachers += 1

        # Формируем текст статистики
        users_text = "👥 Статистика пользователей\n\n"
        
        users_text += "📊 Распределение по группам:\n"
        for group in sorted(group_stats.keys()):
            users_text += f"• {group}: {group_stats[group]} чел.\n"
        
        users_text += f"\n📈 Общая статистика:\n"
        users_text += f"• Всего пользователей: {len(users)}\n"
        users_text += f"• Студентов: {total_students}\n"
        users_text += f"• Преподавателей: {total_teachers}\n"
        users_text += f"• Количество групп: {len(group_stats)}\n"
        
        back_button = [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]]
        await callback.message.edit_text(
            users_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=back_button)
        )
    except Exception as e:
        logger.error(f"Ошибка при получении статистики пользователей: {e}")
        await callback.answer("❌ Произошла ошибка")

@router.callback_query(lambda c: c.data == "admin_cache")
async def admin_cache(callback: CallbackQuery):
    if callback.from_user.id != config.admin_id:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        groups = await db.get_cached_groups()
        teachers = await db.get_cached_teachers()
        
        # Формируем список групп и преподавателей
        groups_list = "\n".join([f"• {group}" for group in sorted(groups)[:5]])
        teachers_list = "\n".join([f"• {teacher}" for teacher in sorted(teachers)[:5]])
        
        # Получаем время последнего обновления
        last_update = await db.get_last_update_time()
        
        cache_text = (
            "💾 *Информация о кэше*\n\n"
            f"📚 Групп в кэше: {len(groups)}\n"
            f"👨‍🏫 Преподавателей в кэше: {len(teachers)}\n\n"
            f"🕒 Последнее обновление: {last_update}"
        )

        back_button = [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]]
        await callback.message.edit_text(
            cache_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=back_button),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при получении информации о кэше: {e}")
        await callback.answer("❌ Произошла ошибка")

@router.callback_query(lambda c: c.data == "admin_update")
async def admin_update(callback: CallbackQuery):
    if callback.from_user.id != config.admin_id:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        await callback.message.edit_text("🔄 Начинаю обновление расписания...")
        
        parser = ScheduleParser()
        schedule_data, groups_list, teachers_list, error = await parser.parse_schedule()

        if error:
            logger.error(f"Ошибка при парсинге: {error}")
            await callback.message.edit_text(
                f"❌ Ошибка при обновлении расписания:\n{error}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
                ]])
            )
            return

        # Обновляем расписание в базе данных
        await db.update_schedule(schedule_data)
        # Обновляем время последнего обновления кэша
        await db.update_cache_time()
        
        update_text = (
            "✅ Расписание успешно обновлено!\n\n"
            f"📊 Статистика:\n"
            f"• Групп: {len(groups_list)}\n"
            f"• Преподавателей: {len(teachers_list)}"
        )
        
        back_button = [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]]
        await callback.message.edit_text(
            update_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=back_button)
        )
    except Exception as e:
        logger.error(f"Ошибка при обновлении расписания: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при обновлении расписания",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
            ]])
        )

@router.callback_query(lambda c: c.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.admin_id:
        await callback.answer("⛔️ У вас нет доступа")
        return

    # Получаем количество пользователей из БД
    users = await db.get_all_users()
    user_count = len(users) if users else 0

    await callback.message.edit_text(
        f"📨 *Отправка сообщения всем пользователям*\n\n"
        f"Всего пользователей: {user_count}\n\n"
        "Введите текст сообщения или нажмите кнопку «Отменить»:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_admin")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
        ])
    )
    await state.set_state(AdminStates.waiting_for_broadcast_message)
@router.callback_query(lambda c: c.data == "admin_send_id")
async def admin_send_id(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.admin_id:
        await callback.answer("⛔️ У вас нет доступа")
        return

    # Получаем список всех пользователей
    users = await db.get_all_users()
    
    if not users:
        await callback.message.edit_text(
            "❌ В базе данных нет пользователей",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
            ]])
        )
        return

    await callback.message.edit_text(
        "👤 *Отправка сообщения по ID*\n\n"
        "Введите ID пользователя, которому хотите отправить сообщение:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")
        ]])
    )
    await state.set_state(AdminStates.waiting_for_user_id)

@router.callback_query(lambda c: c.data == "admin_study_schedule")
async def admin_study_schedule(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.admin_id:
        await callback.answer("⛔️ У вас нет доступа")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 График обр. процесса", callback_data="upload_schedule_edu")],
        [InlineKeyboardButton(text="👥 Спецгруппы", callback_data="upload_schedule_special")],
        [InlineKeyboardButton(text="🔔 Звонки", callback_data="upload_schedule_bells")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
    ])

    await callback.message.edit_text(
        "📋 Управление графиками и расписаниями\n\n"
        "Выберите тип расписания для загрузки:",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data.startswith("upload_schedule_"))
async def schedule_upload_handler(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.admin_id:
        await callback.answer("⛔️ У вас нет доступа")
        return

    schedule_types = {
        "upload_schedule_edu": "график образовательного процесса",
        "upload_schedule_special": "список спецгрупп",
        "upload_schedule_bells": "расписание звонков"
    }

    schedule_type = callback.data
    await state.update_data(schedule_type=schedule_type)
    
    await callback.message.edit_text(
        f"📤 Отправьте фото для раздела «{schedule_types[schedule_type]}»\n\n"
        "Для отмены нажмите кнопку ниже:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="back_to_admin")]
        ])
    )
    await state.set_state(AdminStates.waiting_for_schedule_photo)

@router.message(AdminStates.waiting_for_schedule_photo, F.photo)
async def process_schedule_photo(message: Message, state: FSMContext):
    if message.from_user.id != config.admin_id:
        return

    try:
        state_data = await state.get_data()
        schedule_type = state_data.get('schedule_type')

        # Получаем самую большую версию фото
        photo = message.photo[-1]
        file_id = photo.file_id
        file = await message.bot.get_file(file_id)
        file_path = file.file_path

        # Загружаем фото в Firebase Storage и получаем URL
        schedule_data = {
            'file_id': file_id,
            'file_path': file_path,
            'uploaded_at': firestore.SERVER_TIMESTAMP,
            'uploaded_by': message.from_user.id
        }

        # Сохраняем данные в Firestore
        schedule_types_map = {
            "upload_schedule_edu": "education_schedule",
            "upload_schedule_special": "special_groups",
            "upload_schedule_bells": "bell_schedule"
        }
        
        collection_name = schedule_types_map.get(schedule_type)
        if not collection_name:
            raise ValueError("Неверный тип расписания")

        await db.save_schedule_image(collection_name, schedule_data)

        await message.answer(
            "✅ Фото успешно загружено и сохранено!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад к управлению", callback_data="admin_study_schedule")]
            ])
        )

    except Exception as e:
        logger.error(f"Ошибка при сохранении фото расписания: {e}")
        await message.answer(
            "❌ Произошла ошибка при сохранении фото.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Попробовать снова", callback_data=schedule_type)],
                [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
            ])
        )
    finally:
        await state.clear()

@router.callback_query(lambda c: c.data == "back_to_admin")
async def back_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != config.admin_id:
        await callback.answer("⛔️ У вас нет доступа")
        return

    await state.clear()
    await callback.message.edit_text(
        "🛠 *Панель управления администратора*\n\n"
        "Выберите необходимое действие из меню ниже.",
        reply_markup=get_admin_keyboard()
    )

@router.callback_query(lambda c: c.data == "admin_performance")
async def admin_performance(callback: CallbackQuery):
    if callback.from_user.id != config.admin_id:
        await callback.answer("⛔️ У вас нет доступа")
        return

    try:
        # Получаем отчет о производительности
        report = monitor.get_performance_report()
        
        performance_text = (
            "📊 *Мониторинг производительности*\n\n"
            f"⏱ Время работы: {report['uptime']}\n"
            f"📥 Всего запросов: {report['total_requests']}\n"
            f"❌ Ошибок: {report['error_count']} "
            f"({report['error_rate']:.2f}%)\n\n"
            f"⚡️ Производительность:\n"
            f"• CPU: {report['current_cpu_usage']:.1f}%\n"
            f"• RAM: {report['current_memory_usage']:.1f}%\n"
            f"• Среднее время ответа: {report['avg_response_time']*1000:.1f}ms\n"
            f"• Медленных запросов: {report['slow_requests_count']}\n"
        )
        
        back_button = [[InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]]
        await callback.message.edit_text(
            performance_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=back_button),
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Ошибка при получении метрик производительности: {e}")
        await callback.answer("❌ Произошла ошибка")


