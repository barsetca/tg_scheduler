"""Обработчики создания и редактирования задач"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.keyboards import (
    get_main_menu, get_reminder_time_keyboard, get_periodicity_keyboard,
    get_task_menu, get_edit_task_keyboard, get_calendar_keyboard, get_time_keyboard
)
from utils.navigation import save_navigation_state, get_previous_state
from utils.formatting import format_task_message, format_task_created_message
from utils.validators import validate_time, validate_date, is_date_in_past
from services.task_service import TaskValidationError, task_service
from utils.datetime_utils import local_today
import logging

logger = logging.getLogger(__name__)

router = Router()


class TaskCreationStates(StatesGroup):
    """Состояния для создания задачи"""
    waiting_for_title = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_reminder = State()
    waiting_for_periodicity = State()


class TaskEditStates(StatesGroup):
    """Состояния для редактирования задачи"""
    waiting_for_title = State()
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_reminder = State()
    waiting_for_periodicity = State()


# Создание задачи
@router.message(Command("newtask"))
@router.callback_query(F.data == "new_task")
async def start_new_task(message_or_callback: Message | CallbackQuery, state: FSMContext):
    """Начать создание новой задачи"""
    from utils.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    from utils.navigation import save_navigation_state
    
    # Сохраняем состояние навигации
    await save_navigation_state(state, "main_menu")
    
    # Клавиатура с кнопкой возврата в меню
    cancel_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
        ]
    ])
    
    message_text = (
        "📝 Создание новой задачи\n\n"
        "Введите описание новой задачи в текстовое поле. Для возврата нажмите кнопку Меню."
    )
    
    if isinstance(message_or_callback, CallbackQuery):
        await message_or_callback.message.edit_text(
            message_text,
            reply_markup=cancel_keyboard
        )
        await message_or_callback.answer()
    else:
        await message_or_callback.answer(
            message_text,
            reply_markup=cancel_keyboard
        )
    
    await state.set_state(TaskCreationStates.waiting_for_title)


@router.message(TaskCreationStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    """Обработка названия задачи"""
    title = message.text.strip()
    if not title:
        await message.answer("Описание не может быть пустым. Попробуйте снова:")
        return
    
    await state.update_data(title=title, calendar_context="create")
    await state.set_state(TaskCreationStates.waiting_for_date)
    await save_navigation_state(state, "TaskCreationStates:waiting_for_title")
    
    await message.answer(
        f"Описание сохранено: {title}\n\n"
        "Выберите дату из календаря:",
        reply_markup=get_calendar_keyboard(prefix="calendar")
    )


@router.message(TaskCreationStates.waiting_for_date)
async def process_date(message: Message, state: FSMContext):
    """Обработка даты (текстовый ввод как альтернатива календарю)"""
    # Проверяем, не является ли это командой
    if message.text and message.text.startswith("/"):
        # Если это команда, не обрабатываем здесь
        return
    
    text = message.text.strip().lower()
    
    if text == "сегодня" or text == "":
        task_date = local_today()
    else:
        is_valid, date_obj = validate_date(text)
        if not is_valid or not date_obj:
            await message.answer(
                "Неверный формат даты. Используйте календарь или введите дату в формате DD.MM.YYYY"
            )
            return
        
        if is_date_in_past(date_obj):
            await message.answer(
                "Дата не может быть в прошлом. Выберите другую дату из календаря:",
                reply_markup=get_calendar_keyboard(prefix="calendar")
            )
            return
        
        task_date = date_obj
    
    await state.update_data(task_date=task_date)
    await state.set_state(TaskCreationStates.waiting_for_time)
    await save_navigation_state(state, "TaskCreationStates:waiting_for_date")
    await message.answer(
        f"✅ Дата установлена: {task_date.strftime('%d.%m.%Y')}\n\n"
        "Установить время? (введите в формате HH:MM или отправьте 'нет' для пропуска)"
    )


@router.message(TaskCreationStates.waiting_for_time)
async def process_time(message: Message, state: FSMContext):
    """Обработка времени (текстовый ввод как альтернатива клавиатуре)"""
    text = message.text.strip().lower()
    
    if text == "нет" or text == "":
        task_time = None
        await state.update_data(task_time=None, reminder_time=0)
        await state.set_state(TaskCreationStates.waiting_for_periodicity)
        await save_navigation_state(state, "TaskCreationStates:waiting_for_time")
        await message.answer(
            "Время не установлено.\n\nПериодичность задачи:",
            reply_markup=get_periodicity_keyboard("back")
        )
    else:
        is_valid, time_obj = validate_time(text)
        if not is_valid or not time_obj:
            from utils.keyboards import get_time_keyboard
            data = await state.get_data()
            hours = data.get("time_hours", 12)
            minutes = data.get("time_minutes", 0)
            await state.update_data(time_context="create")
            await message.answer(
                "Неверный формат времени. Используйте клавиатуру или введите HH:MM",
                reply_markup=get_time_keyboard(hours=hours, minutes=minutes, prefix="time_create")
            )
            return
        task_time = time_obj
        await state.update_data(task_time=task_time)
        await state.set_state(TaskCreationStates.waiting_for_reminder)
        await save_navigation_state(state, "TaskCreationStates:waiting_for_time")
        await message.answer(
            f"✅ Время установлено: {task_time.strftime('%H:%M')}\n\n"
            "За сколько времени напомнить?",
            reply_markup=get_reminder_time_keyboard("back")
        )


@router.callback_query(F.data.startswith("reminder_"), TaskCreationStates.waiting_for_reminder)
async def process_reminder(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени напоминания"""
    if callback.data == "back":
        # Возврат на предыдущий шаг
        previous_state = await get_previous_state(state)
        if previous_state == "TaskCreationStates:waiting_for_time":
            await state.set_state(TaskCreationStates.waiting_for_time)
            data = await state.get_data()
            task_date = data.get("task_date", local_today())
            await callback.message.edit_text(
                f"Дата: {task_date.strftime('%d.%m.%Y')}\n\n"
                "Установить время? (введите в формате HH:MM или отправьте 'нет' для пропуска)"
            )
            await callback.answer()
            return
    
    # Обработка отмены напоминания
    if callback.data == "reminder_cancel":
        await state.update_data(reminder_time=-1)
        await state.set_state(TaskCreationStates.waiting_for_periodicity)
        await save_navigation_state(state, "TaskCreationStates:waiting_for_reminder")
        
        await callback.message.edit_text(
            "Напоминание отменено\n\n"
            "Периодичность задачи:",
            reply_markup=get_periodicity_keyboard("back")
        )
        await callback.answer("✅ Напоминание отменено")
        return
    
    minutes = int(callback.data.split("_")[1])
    await state.update_data(reminder_time=minutes)
    await state.set_state(TaskCreationStates.waiting_for_periodicity)
    await save_navigation_state(state, "TaskCreationStates:waiting_for_reminder")
    
    # Форматирование времени напоминания
    if minutes == 1440:
        reminder_text = "за 1 сутки"
    elif minutes == 10080:
        reminder_text = "за 1 неделю"
    elif minutes == 0:
        reminder_text = "в момент задачи"
    else:
        reminder_text = f"за {minutes} минут"
    
    await callback.message.edit_text(
        f"Напоминание установлено: {reminder_text}\n\n"
        "Периодичность задачи:",
        reply_markup=get_periodicity_keyboard("back")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("period_"), TaskCreationStates.waiting_for_periodicity)
async def process_periodicity(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора периодичности"""
    if callback.data == "back":
        # Возврат на предыдущий шаг
        previous_state = await get_previous_state(state)
        if previous_state == "TaskCreationStates:waiting_for_reminder":
            await state.set_state(TaskCreationStates.waiting_for_reminder)
            data = await state.get_data()
            task_time = data.get("task_time")
            if task_time:
                await callback.message.edit_text(
                    f"Время: {task_time.strftime('%H:%M')}\n\n"
                    "За сколько времени напомнить?",
                    reply_markup=get_reminder_time_keyboard("back")
                )
            else:
                await state.set_state(TaskCreationStates.waiting_for_periodicity)
                await callback.message.edit_text(
                    "Периодичность задачи:",
                    reply_markup=get_periodicity_keyboard("back")
                )
            await callback.answer()
            return
    
    periodicity = callback.data.split("_")[1]
    periodicity_map = {
        "none": "none",
        "hourly": "hourly",
        "daily": "daily",
        "weekly": "weekly",
        "monthly": "monthly",
        "yearly": "yearly"
    }
    periodicity_value = periodicity_map.get(periodicity, "none")
    
    data = await state.get_data()
    
    try:
        # Проверка на дублирование времени
        task_date = data["task_date"]
        task_time = data.get("task_time")
        
        if task_time:
            from database import db
            existing_tasks = await db.get_tasks_by_datetime(
                user_id=callback.from_user.id,
                task_date=task_date,
                task_time=task_time
            )
            
            if existing_tasks:
                existing_task = existing_tasks[0]
                task_time_str = task_time.strftime('%H:%M')
                existing_title = existing_task.get('title', 'Без названия')
                await callback.message.edit_text(
                    f"⚠️ На это время ({task_time_str}) уже назначена задача:\n\n"
                    f"📋 {existing_title}\n\n"
                    f"Выберите другое время или измените предыдущую задачу:",
                    reply_markup=get_periodicity_keyboard("back")
                )
                await callback.answer(f"⚠️ На это время уже есть задача: {existing_title}", show_alert=True)
                return
        
        task_id = await task_service.create_task(
            user_id=callback.from_user.id,
            title=data["title"],
            description=None,
            task_date=task_date,
            task_time=task_time,
            reminder_time=data.get("reminder_time", 0),
            periodicity=periodicity_value
        )
        
        task = await task_service.get_task(task_id, callback.from_user.id)
        await callback.message.edit_text(
            format_task_created_message(task),
            reply_markup=get_task_menu(task_id, "back")
        )
        await callback.answer("✅ Задача создана!")
        await state.clear()
    except TaskValidationError as e:
        await callback.message.edit_text(str(e), reply_markup=get_main_menu())
        await callback.answer(str(e), show_alert=True)
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при создании задачи: {e}")
        await callback.message.edit_text(
            "❌ Ошибка сервера. Попробуйте позже.",
            reply_markup=get_main_menu()
        )
        await callback.answer("Ошибка!")
        await state.clear()


# Редактирование задачи
@router.callback_query(F.data.startswith("edit_task_"))
async def start_edit_task(callback: CallbackQuery, state: FSMContext):
    """Начать редактирование задачи"""
    task_id = int(callback.data.split("_")[2])
    task = await task_service.get_task(task_id, callback.from_user.id)
    
    if not task:
        await callback.answer("Задача не найдена!")
        return
    
    await state.update_data(task_id=task_id)
    from utils.navigation import save_navigation_state
    await save_navigation_state(state, f"view_task_{task_id}")
    await state.update_data(edit_previous_state=f"view_task_{task_id}")
    await callback.message.edit_text(
        "Что вы хотите изменить?",
        reply_markup=get_edit_task_keyboard(task_id, f"view_task_{task_id}")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_title_"))
async def edit_title(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия"""
    task_id = int(callback.data.split("_")[2])
    await state.update_data(task_id=task_id)
    await state.set_state(TaskEditStates.waiting_for_title)
    from utils.navigation import save_navigation_state
    await save_navigation_state(state, "edit_task")
    await callback.message.edit_text("Введите новое описание задачи:")
    await callback.answer()


@router.message(TaskEditStates.waiting_for_title)
async def process_edit_title(message: Message, state: FSMContext):
    """Обработка нового названия"""
    data = await state.get_data()
    task_id = data["task_id"]
    title = message.text.strip()
    
    if not title:
        await message.answer("Описание не может быть пустым. Попробуйте снова:")
        return
    
    try:
        await task_service.update_task(task_id, message.from_user.id, title=title)
        task = await task_service.get_task(task_id, message.from_user.id)
        await message.answer(
            f"✅ Задача обновлена!\n\n{format_task_message(task)}",
            reply_markup=get_task_menu(task_id, "back")
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обновлении задачи: {e}")
        await message.answer("❌ Ошибка сервера. Попробуйте позже.")


@router.callback_query(F.data.startswith("edit_date_"))
async def edit_date(callback: CallbackQuery, state: FSMContext):
    """Редактирование даты"""
    task_id = int(callback.data.split("_")[2])
    task = await task_service.get_task(task_id, callback.from_user.id)
    if not task:
        await callback.answer("Задача не найдена!")
        return
    
    selected_date = None
    if task and task.get("task_date"):
        from datetime import date as dt_date
        task_date_str = task.get("task_date")
        selected_date = dt_date.fromisoformat(task_date_str) if isinstance(task_date_str, str) else task_date_str
    
    await state.update_data(task_id=task_id, calendar_context="edit", task_date=selected_date)
    await state.set_state(TaskEditStates.waiting_for_date)
    from utils.navigation import save_navigation_state
    await save_navigation_state(state, "edit_task")
    await callback.message.edit_text(
        "Выберите новую дату из календаря:",
        reply_markup=get_calendar_keyboard(selected_date=selected_date, prefix="calendar")
    )
    await callback.answer()


@router.message(TaskEditStates.waiting_for_date)
async def process_edit_date(message: Message, state: FSMContext):
    """Обработка новой даты"""
    # Проверяем, не является ли это командой
    if message.text and message.text.startswith("/"):
        # Если это команда, не обрабатываем здесь
        return
    
    data = await state.get_data()
    task_id = data["task_id"]
    text = message.text.strip().lower()
    
    if text == "сегодня":
        task_date = local_today()
    else:
        is_valid, date_obj = validate_date(text)
        if not is_valid or not date_obj:
            await message.answer("Неверный формат даты. Попробуйте снова:")
            return
        task_date = date_obj
    
    try:
        await task_service.update_task(task_id, message.from_user.id, task_date=task_date)
        task = await task_service.get_task(task_id, message.from_user.id)
        await message.answer(
            f"✅ Задача обновлена!\n\n{format_task_message(task)}",
            reply_markup=get_task_menu(task_id, "back")
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обновлении задачи: {e}")
        await message.answer("❌ Ошибка сервера. Попробуйте позже.")


@router.callback_query(F.data.startswith("edit_time_"))
async def edit_time(callback: CallbackQuery, state: FSMContext):
    """Редактирование времени"""
    task_id = int(callback.data.split("_")[2])
    task = await task_service.get_task(task_id, callback.from_user.id)
    
    if not task:
        await callback.answer("Задача не найдена!")
        return
    
    # Получаем текущее время задачи
    hours, minutes = 12, 0
    if task and task.get("task_time"):
        from datetime import time as dt_time
        task_time_str = task.get("task_time")
        task_time = dt_time.fromisoformat(task_time_str) if isinstance(task_time_str, str) else task_time_str
        hours = task_time.hour
        minutes = task_time.minute
    
    await state.update_data(
        task_id=task_id,
        time_hours=hours,
        time_minutes=minutes,
        time_context="edit"
    )
    await state.set_state(TaskEditStates.waiting_for_time)
    from utils.navigation import save_navigation_state
    await save_navigation_state(state, "edit_task")
    await callback.message.edit_text(
        "Выберите новое время:",
        reply_markup=get_time_keyboard(hours, minutes, prefix="time_edit")
    )
    await callback.answer()


@router.message(TaskEditStates.waiting_for_time)
async def process_edit_time(message: Message, state: FSMContext):
    """Обработка нового времени (текстовый ввод как альтернатива)"""
    data = await state.get_data()
    task_id = data["task_id"]
    text = message.text.strip().lower()
    
    if text == "нет":
        task_time = None
    else:
        is_valid, time_obj = validate_time(text)
        if not is_valid or not time_obj:
            from utils.keyboards import get_time_keyboard
            hours = data.get("time_hours", 12)
            minutes = data.get("time_minutes", 0)
            await message.answer(
                "Неверный формат времени. Используйте клавиатуру или введите HH:MM",
                reply_markup=get_time_keyboard(hours, minutes, prefix="time_edit")
            )
            return
        task_time = time_obj
    
    try:
        await task_service.update_task(task_id, message.from_user.id, task_time=task_time)
        task = await task_service.get_task(task_id, message.from_user.id)
        await message.answer(
            f"✅ Задача обновлена!\n\n{format_task_message(task)}",
            reply_markup=get_task_menu(task_id, "back")
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обновлении задачи: {e}")
        await message.answer("❌ Ошибка сервера. Попробуйте позже.")


@router.callback_query(F.data.startswith("edit_reminder_"))
async def edit_reminder(callback: CallbackQuery, state: FSMContext):
    """Редактирование напоминания"""
    task_id = int(callback.data.split("_")[2])
    await state.update_data(task_id=task_id)
    await state.set_state(TaskEditStates.waiting_for_reminder)
    from utils.navigation import save_navigation_state
    await save_navigation_state(state, "edit_task")
    await callback.message.edit_text(
        "За сколько минут напомнить?",
        reply_markup=get_reminder_time_keyboard("back")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reminder_"), TaskEditStates.waiting_for_reminder)
async def process_edit_reminder(callback: CallbackQuery, state: FSMContext):
    """Обработка нового времени напоминания"""
    if callback.data == "back":
        data = await state.get_data()
        task_id = data.get("task_id")
        if task_id:
            task = await task_service.get_task(task_id, callback.from_user.id)
            await callback.message.edit_text(
                format_task_message(task),
                reply_markup=get_task_menu(task_id, "back")
            )
            await state.clear()
            await callback.answer()
            return
    
    # Обработка отмены напоминания
    if callback.data == "reminder_cancel":
        data = await state.get_data()
        task_id = data.get("task_id")
        if task_id:
            await task_service.update_task(task_id, callback.from_user.id, reminder_time=-1)
            task = await task_service.get_task(task_id, callback.from_user.id)
            await callback.message.edit_text(
                f"✅ Напоминание отменено!\n\n{format_task_message(task)}",
                reply_markup=get_task_menu(task_id, "back")
            )
            await state.clear()
            await callback.answer("✅ Напоминание отменено")
            return
    
    if callback.data == "cancel":
        data = await state.get_data()
        task_id = data.get("task_id")
        if task_id:
            task = await task_service.get_task(task_id, callback.from_user.id)
            await callback.message.edit_text(
                format_task_message(task),
                reply_markup=get_task_menu(task_id)
            )
        else:
            await callback.message.edit_text(
                "Редактирование отменено.",
                reply_markup=get_main_menu()
            )
        await state.clear()
        await callback.answer("Отменено")
        return
    
    data = await state.get_data()
    task_id = data["task_id"]
    minutes = int(callback.data.split("_")[1])
    
    try:
        await task_service.update_task(
            task_id, callback.from_user.id, reminder_time=minutes
        )
        
        task = await task_service.get_task(task_id, callback.from_user.id)
        await callback.message.edit_text(
            f"✅ Задача обновлена!\n\n{format_task_message(task)}",
            reply_markup=get_task_menu(task_id)
        )
        await callback.answer("✅ Обновлено!")
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обновлении задачи: {e}")
        await callback.message.edit_text("❌ Ошибка сервера. Попробуйте позже.")
        await callback.answer("Ошибка!")


@router.callback_query(F.data.startswith("edit_periodicity_"))
async def edit_periodicity(callback: CallbackQuery, state: FSMContext):
    """Редактирование периодичности"""
    task_id = int(callback.data.split("_")[2])
    await state.update_data(task_id=task_id)
    await state.set_state(TaskEditStates.waiting_for_periodicity)
    from utils.navigation import save_navigation_state
    await save_navigation_state(state, "edit_task")
    await callback.message.edit_text(
        "Выберите периодичность:",
        reply_markup=get_periodicity_keyboard("back")
    )
    await callback.answer()


@router.callback_query(F.data.startswith("period_"), TaskEditStates.waiting_for_periodicity)
async def process_edit_periodicity(callback: CallbackQuery, state: FSMContext):
    """Обработка новой периодичности"""
    if callback.data == "cancel":
        data = await state.get_data()
        task_id = data.get("task_id")
        if task_id:
            task = await task_service.get_task(task_id, callback.from_user.id)
            await callback.message.edit_text(
                format_task_message(task),
                reply_markup=get_task_menu(task_id)
            )
        else:
            await callback.message.edit_text(
                "Редактирование отменено.",
                reply_markup=get_main_menu()
            )
        await state.clear()
        await callback.answer("Отменено")
        return
    
    data = await state.get_data()
    task_id = data["task_id"]
    periodicity = callback.data.split("_")[1]
    periodicity_map = {
        "none": "none",
        "hourly": "hourly",
        "daily": "daily",
        "weekly": "weekly",
        "monthly": "monthly",
        "yearly": "yearly"
    }
    periodicity_value = periodicity_map.get(periodicity, "none")
    
    try:
        await task_service.update_task(
            task_id, callback.from_user.id, periodicity=periodicity_value
        )
        task = await task_service.get_task(task_id, callback.from_user.id)
        await callback.message.edit_text(
            f"✅ Задача обновлена!\n\n{format_task_message(task)}",
            reply_markup=get_task_menu(task_id)
        )
        await callback.answer("✅ Обновлено!")
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при обновлении задачи: {e}")
        await callback.message.edit_text("❌ Ошибка сервера. Попробуйте позже.")
        await callback.answer("Ошибка!")
