"""Обработчики напоминаний"""
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from utils.keyboards import get_reminder_actions, get_task_menu
from utils.formatting import format_reminder_message
from services.reminder_service import reminder_service
from services.task_service import task_service
from utils.validators import validate_minutes
import logging

logger = logging.getLogger(__name__)

router = Router()


class PostponeStates(StatesGroup):
    """Состояния для откладывания напоминания"""
    waiting_for_minutes = State()


@router.callback_query(F.data.startswith("postpone_"))
async def start_postpone(callback: CallbackQuery, state: FSMContext):
    """Начать откладывание напоминания"""
    parts = callback.data.split("_")
    reminder_id = int(parts[1])
    task_id = int(parts[2])
    
    # Проверяем, что задача принадлежит пользователю
    task = await task_service.get_task(task_id, callback.from_user.id)
    if not task:
        await callback.answer("❌ Задача не найдена или не принадлежит вам!")
        return
    
    await state.update_data(reminder_id=reminder_id, task_id=task_id)
    await state.set_state(PostponeStates.waiting_for_minutes)
    
    await callback.message.edit_text(
        "На сколько минут отложить напоминание? (введите число)"
    )
    await callback.answer()


@router.message(PostponeStates.waiting_for_minutes)
async def process_postpone(message: Message, state: FSMContext):
    """Обработка откладывания напоминания"""
    data = await state.get_data()
    reminder_id = data["reminder_id"]
    task_id = data["task_id"]
    
    is_valid, minutes = validate_minutes(message.text.strip())
    if not is_valid or not minutes:
        await message.answer(
            "Неверный формат. Введите число минут (от 1 до 1440):"
        )
        return
    
    try:
        # Проверяем, что напоминание принадлежит пользователю
        reminder = await reminder_service.get_reminder_by_id(reminder_id, message.from_user.id)
        if not reminder:
            await message.answer("❌ Напоминание не найдено или не принадлежит вам.")
            await state.clear()
            return
        
        # Откладываем напоминание
        success = await reminder_service.postpone_reminder(reminder_id, message.from_user.id, minutes)
        if not success:
            await message.answer("❌ Не удалось отложить напоминание.")
            await state.clear()
            return
        
        task = await task_service.get_task(task_id, message.from_user.id)
        if not task:
            await message.answer("❌ Задача не найдена.")
            await state.clear()
            return
        
        new_time = datetime.now() + timedelta(minutes=minutes)
        await message.answer(
            f"✅ Напоминание отложено на {new_time.strftime('%H:%M')}\n\n"
            f"{format_reminder_message(task, minutes)}",
            reply_markup=get_reminder_actions(task_id, reminder_id)
        )
        await state.clear()
    except Exception as e:
        logger.error(f"Ошибка при откладывании напоминания: {e}")
        await message.answer("❌ Ошибка сервера. Попробуйте позже.")
        await state.clear()

