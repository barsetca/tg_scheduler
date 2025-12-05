"""Обработчики callback-кнопок"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from utils.keyboards import (
    get_main_menu, get_task_menu, get_confirm_delete_keyboard
)
from utils.formatting import format_task_message
from utils.navigation import get_previous_state
from services.task_service import task_service
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("complete_task_"))
async def complete_task(callback: CallbackQuery):
    """Завершить задачу"""
    task_id = int(callback.data.split("_")[2])
    try:
        # Получаем задачу для проверки даты
        task = await task_service.get_task(task_id, callback.from_user.id)
        if not task:
            await callback.answer("Задача не найдена!", show_alert=True)
            return
        
        # Проверяем, что задача не в будущем
        from datetime import date
        task_date_str = task.get("task_date")
        if task_date_str:
            if isinstance(task_date_str, str):
                task_date = date.fromisoformat(task_date_str)
            else:
                task_date = task_date_str
            
            today = date.today()
            if task_date > today:
                await callback.answer(
                    "❌ Нельзя завершить задачу с будущей датой!",
                    show_alert=True
                )
                return
        
        # Завершаем задачу
        task = await task_service.complete_task(task_id, callback.from_user.id)
        if not task:
            await callback.answer("Задача не найдена!", show_alert=True)
            return
        
        await callback.message.edit_text(
            f"✅ Задача завершена!\n\n{format_task_message(task)}",
            reply_markup=get_main_menu()
        )
        await callback.answer("✅ Задача завершена!")
    except Exception as e:
        logger.error(f"Ошибка при завершении задачи: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Ошибка сервера. Попробуйте позже.",
            reply_markup=get_main_menu()
        )
        await callback.answer("Ошибка!", show_alert=True)


@router.callback_query(F.data.startswith("delete_task_"))
async def delete_task_confirm(callback: CallbackQuery):
    """Подтверждение удаления задачи"""
    task_id = int(callback.data.split("_")[2])
    task = await task_service.get_task(task_id, callback.from_user.id)
    
    if not task:
        await callback.answer("Задача не найдена!")
        return
    
    await callback.message.edit_text(
        f"Вы уверены, что хотите удалить задачу?\n\n"
        f"{format_task_message(task)}",
        reply_markup=get_confirm_delete_keyboard(task_id)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_"))
async def confirm_delete(callback: CallbackQuery):
    """Подтвержденное удаление задачи"""
    task_id = int(callback.data.split("_")[2])
    try:
        success = await task_service.delete_task(task_id, callback.from_user.id)
        if not success:
            await callback.answer("Задача не найдена!")
            return
        
        await callback.message.edit_text(
            "🗑️ Задача удалена.",
            reply_markup=get_main_menu()
        )
        await callback.answer("✅ Задача удалена!")
    except Exception as e:
        logger.error(f"Ошибка при удалении задачи: {e}")
        await callback.message.edit_text(
            "❌ Ошибка сервера. Попробуйте позже.",
            reply_markup=get_main_menu()
        )
        await callback.answer("Ошибка!")


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена действия"""
    await state.clear()
    await callback.message.edit_text(
        "Действие отменено.",
        reply_markup=get_main_menu()
    )
    await callback.answer("Отменено")


@router.callback_query(F.data == "back")
async def back_action(callback: CallbackQuery, state: FSMContext):
    """Обработка кнопки Назад с историей навигации"""
    try:
        previous_state = await get_previous_state(state)
        
        if previous_state:
            # Восстанавливаем предыдущее состояние
            if previous_state.startswith("view_task_"):
                task_id = int(previous_state.split("_")[2])
                task = await task_service.get_task(task_id, callback.from_user.id)
                if task:
                    from utils.formatting import format_task_message
                    await callback.message.edit_text(
                        format_task_message(task),
                        reply_markup=get_task_menu(task_id, "back")
                    )
                    await callback.answer()
                    return
            elif previous_state == "tasks_today":
                from handlers.view import show_tasks_today
                await show_tasks_today(callback, state)
                return
            elif previous_state == "main_menu":
                from handlers.start import callback_main_menu
                await callback_main_menu(callback)
                return
            elif previous_state == "TaskCreationStates:waiting_for_date":
                # Возврат к выбору даты
                from utils.keyboards import get_calendar_keyboard
                await state.set_state("TaskCreationStates:waiting_for_date")
                await callback.message.edit_text(
                    "Выберите дату из календаря:",
                    reply_markup=get_calendar_keyboard(prefix="calendar")
                )
                await callback.answer()
                return
            elif previous_state == "TaskCreationStates:waiting_for_time":
                # Возврат к выбору времени
                from utils.keyboards import get_time_keyboard
                data = await state.get_data()
                hours = data.get("time_hours", 12)
                minutes = data.get("time_minutes", 0)
                await state.set_state("TaskCreationStates:waiting_for_time")
                await state.update_data(time_context="create")
                await callback.message.edit_text(
                    f"Дата: {data.get('task_date', date.today()).strftime('%d.%m.%Y')}\n\n"
                    "Выберите время или нажмите 'Пропустить':",
                    reply_markup=get_time_keyboard(hours=hours, minutes=minutes, prefix="time_create")
                )
                await callback.answer()
                return
            elif previous_state == "TaskCreationStates:waiting_for_reminder":
                # Возврат к выбору напоминания
                from utils.keyboards import get_reminder_time_keyboard
                data = await state.get_data()
                task_time = data.get("task_time")
                if task_time:
                    await state.set_state("TaskCreationStates:waiting_for_reminder")
                    await callback.message.edit_text(
                        f"Время: {task_time.strftime('%H:%M')}\n\n"
                        "За сколько времени напомнить?",
                        reply_markup=get_reminder_time_keyboard("back")
                    )
                    await callback.answer()
                    return
            elif previous_state == "edit_task":
                # Возврат к меню редактирования задачи
                data = await state.get_data()
                task_id = data.get("task_id")
                if task_id:
                    task = await task_service.get_task(task_id, callback.from_user.id)
                    if task:
                        from utils.keyboards import get_edit_task_keyboard
                        await callback.message.edit_text(
                            "Что вы хотите изменить?",
                            reply_markup=get_edit_task_keyboard(task_id, f"view_task_{task_id}")
                        )
                        await callback.answer()
                        return
            elif previous_state == "main_menu":
                # Возврат в главное меню
                from handlers.start import callback_main_menu
                await callback_main_menu(callback)
                return
        
        # Если истории нет или не удалось восстановить, идем в главное меню
        await callback.message.edit_text(
            "👋 Главное меню\n\nВыберите действие:",
            reply_markup=get_main_menu()
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки Назад: {e}")
        await callback.message.edit_text(
            "👋 Главное меню\n\nВыберите действие:",
            reply_markup=get_main_menu()
        )
        await callback.answer("Ошибка")

