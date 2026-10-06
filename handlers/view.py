"""Обработчики просмотра задач"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date
from utils.keyboards import (
    get_main_menu, get_task_menu, get_tasks_list_keyboard, get_date_filters
)
from utils.formatting import format_tasks_list, format_task_message
from utils.validators import validate_date
from services.task_service import task_service
from utils.datetime_utils import local_today
import logging

logger = logging.getLogger(__name__)

router = Router()


class DateFilterStates(StatesGroup):
    """Состояния для фильтрации по дате"""
    waiting_for_date = State()


@router.callback_query(F.data == "tasks_today")
async def show_tasks_today(callback: CallbackQuery, state: FSMContext):
    """Показать задачи на сегодня"""
    try:
        # Сохраняем состояние навигации
        from utils.navigation import save_navigation_state
        await save_navigation_state(state, "main_menu")
        
        today = local_today()
        tasks = await task_service.get_tasks_by_date(
            user_id=callback.from_user.id,
            task_date=today,
            show_completed=True
        )
        
        # Сохраняем дату и задачи в состоянии для кнопки "Редактировать"
        await state.update_data(selected_date=today.isoformat())
        
        message = format_tasks_list(tasks, today)
        
        if tasks:
            from utils.keyboards import get_tasks_view_keyboard
            keyboard = get_tasks_view_keyboard("back")
        else:
            from utils.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="◀️ Назад", callback_data="back"),
                    InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
                ]
            ])
        
        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении задач: {e}")
        await callback.message.edit_text(
            "❌ Ошибка сервера. Попробуйте позже.",
            reply_markup=get_main_menu()
        )
        await callback.answer("Ошибка!")


@router.callback_query(F.data == "tasks_date")
async def start_tasks_date(callback: CallbackQuery, state: FSMContext):
    """Начать выбор даты для просмотра задач"""
    from utils.keyboards import get_calendar_keyboard
    from utils.navigation import save_navigation_state
    await state.update_data(calendar_context="view_tasks")
    await save_navigation_state(state, "main_menu")
    await callback.message.edit_text(
        "Выберите дату из календаря:",
        reply_markup=get_calendar_keyboard(prefix="calendar_view")
    )
    await callback.answer()


@router.message(Command("tasksdate"))
async def cmd_tasks_date(message: Message, state: FSMContext):
    """Команда для просмотра задач по дате"""
    from utils.keyboards import get_calendar_keyboard
    from utils.navigation import save_navigation_state
    # Очищаем состояние, чтобы избежать конфликтов с другими обработчиками
    await state.clear()
    await state.update_data(calendar_context="view_tasks")
    await save_navigation_state(state, "main_menu")
    await message.answer(
        "Выберите дату из календаря:",
        reply_markup=get_calendar_keyboard(prefix="calendar_view")
    )


@router.message(DateFilterStates.waiting_for_date)
async def process_date_filter(message: Message, state: FSMContext):
    """Обработка выбранной даты"""
    # Проверяем, не является ли это командой
    if message.text and message.text.startswith("/"):
        # Если это команда, не обрабатываем здесь
        return
    
    text = message.text.strip().lower()
    
    if text == "сегодня":
        task_date = local_today()
    else:
        is_valid, date_obj = validate_date(text)
        if not is_valid or not date_obj:
            await message.answer(
                "Неверный формат даты. Используйте DD.MM.YYYY или DD.MM, "
                "или отправьте 'сегодня'"
            )
            return
        task_date = date_obj
    
    try:
        tasks = await task_service.get_tasks_by_date(
            user_id=message.from_user.id,
            task_date=task_date,
            show_completed=True
        )
        
        # Сохраняем дату в состоянии для кнопки "Редактировать"
        await state.update_data(selected_date=task_date.isoformat())
        
        message_text = format_tasks_list(tasks, task_date)
        
        if tasks:
            from utils.keyboards import get_tasks_view_keyboard
            keyboard = get_tasks_view_keyboard("back")
        else:
            message_text += "\n\nВыберите фильтр:"
            keyboard = get_date_filters("back")
        
        await message.answer(
            message_text,
            reply_markup=keyboard
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при получении задач: {e}")
        await message.answer("❌ Ошибка сервера. Попробуйте позже.")


@router.callback_query(F.data == "filter_all")
async def filter_all(callback: CallbackQuery, state: FSMContext):
    """Показать все задачи"""
    # Получаем дату из состояния или используем сегодня
    state_data = await state.get_data()
    selected_date_str = state_data.get("selected_date")
    
    if selected_date_str:
        try:
            task_date = date.fromisoformat(selected_date_str)
        except (ValueError, TypeError):
            task_date = local_today()
    else:
        task_date = local_today()
    
    try:
        tasks = await task_service.get_tasks_by_date(
            user_id=callback.from_user.id,
            task_date=task_date,
            show_completed=True
        )
        # Сохраняем дату в состоянии для кнопки "Редактировать"
        await state.update_data(selected_date=task_date.isoformat())
        
        message = format_tasks_list(tasks, task_date)
        from utils.keyboards import get_tasks_view_keyboard
        keyboard = get_tasks_view_keyboard("back") if tasks else get_main_menu()
        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении задач: {e}")
        await callback.answer("Ошибка!")


@router.callback_query(F.data == "filter_completed")
async def filter_completed(callback: CallbackQuery, state: FSMContext):
    """Показать только выполненные задачи"""
    # Получаем дату из состояния или используем сегодня
    state_data = await state.get_data()
    selected_date_str = state_data.get("selected_date")
    
    if selected_date_str:
        try:
            task_date = date.fromisoformat(selected_date_str)
        except (ValueError, TypeError):
            task_date = local_today()
    else:
        task_date = local_today()
    
    try:
        tasks = await task_service.get_tasks_by_date(
            user_id=callback.from_user.id,
            task_date=task_date,
            show_completed=True
        )
        # Фильтруем только выполненные
        completed_tasks = [t for t in tasks if t.get("is_completed")]
        # Сохраняем дату в состоянии для кнопки "Редактировать"
        await state.update_data(selected_date=task_date.isoformat())
        
        message = format_tasks_list(completed_tasks, task_date)
        from utils.keyboards import get_tasks_view_keyboard
        keyboard = get_tasks_view_keyboard("back") if completed_tasks else get_main_menu()
        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении задач: {e}")
        await callback.answer("Ошибка!")


@router.callback_query(F.data == "filter_overdue")
async def filter_overdue(callback: CallbackQuery, state: FSMContext):
    """Показать просроченные задачи"""
    try:
        today = local_today()
        tasks = await task_service.get_tasks_by_date(
            user_id=callback.from_user.id,
            task_date=today,
            show_completed=False,
            show_overdue=True
        )
        # Сохраняем дату в состоянии для кнопки "Редактировать"
        await state.update_data(selected_date=today.isoformat())
        
        message = "📋 Просроченные задачи\n\n"
        if tasks:
            message += format_tasks_list(tasks, today)
        else:
            message += "Просроченных задач нет."
        from utils.keyboards import get_tasks_view_keyboard
        keyboard = get_tasks_view_keyboard("back") if tasks else get_main_menu()
        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении задач: {e}")
        await callback.answer("Ошибка!")


@router.callback_query(F.data == "edit_tasks_list")
async def edit_tasks_list(callback: CallbackQuery, state: FSMContext):
    """Показать список задач для редактирования (текущая реализация с кнопками)"""
    try:
        # Получаем дату из состояния
        state_data = await state.get_data()
        selected_date_str = state_data.get("selected_date")
        
        if selected_date_str:
            try:
                task_date = date.fromisoformat(selected_date_str)
            except (ValueError, TypeError):
                task_date = local_today()
        else:
            task_date = local_today()
        
        # Сохраняем дату в состоянии для навигации
        await state.update_data(selected_date=task_date.isoformat())
        
        # Получаем задачи на эту дату
        tasks = await task_service.get_tasks_by_date(
            user_id=callback.from_user.id,
            task_date=task_date,
            show_completed=True
        )
        
        if not tasks:
            await callback.answer("Нет задач для редактирования", show_alert=True)
            return
        
        # Показываем текущую реализацию с кнопками задач
        message = format_tasks_list(tasks, task_date)
        message += "\n\nВыберите задачу для редактирования:"
        
        keyboard = get_tasks_list_keyboard(tasks, "view_task", "back")
        await callback.message.edit_text(message, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении задач для редактирования: {e}")
        await callback.answer("Ошибка!")


@router.callback_query(F.data.startswith("view_task_"))
async def view_task(callback: CallbackQuery, state: FSMContext):
    """Просмотр конкретной задачи"""
    task_id = int(callback.data.split("_")[2])
    try:
        task = await task_service.get_task(task_id, callback.from_user.id)
        if not task:
            await callback.answer("Задача не найдена!")
            return
        
        # Сохраняем текущее состояние (список задач) в историю навигации
        from utils.navigation import save_navigation_state
        # Сохраняем состояние "tasks_today" как предыдущее перед переходом к задаче
        await save_navigation_state(state, "tasks_today")
        
        message = format_task_message(task)
        await callback.message.edit_text(
            message,
            reply_markup=get_task_menu(task_id, "back")
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при получении задачи: {e}")
        await callback.answer("Ошибка!")
