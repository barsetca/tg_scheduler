"""Обработчики удаления задач"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import timedelta
from utils.keyboards import (
    get_main_menu, get_delete_tasks_interval_keyboard, get_confirm_delete_tasks_keyboard
)
from utils.navigation import save_navigation_state
from utils.constants import DELETE_INTERVALS
from utils.task_filters import filter_tasks_by_time
from database import db
from utils.datetime_utils import local_now, local_today
from services.task_service import task_service
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data == "delete_one_time_tasks")
async def start_delete_one_time_tasks(callback: CallbackQuery, state: FSMContext):
    """Начать процесс удаления одноразовых задач"""
    await save_navigation_state(state, "main_menu")
    await callback.message.edit_text(
        "🗑️ Удаление одноразовых задач\n\n"
        "Выберите интервал для удаления задач:\n"
        "⚠️ Будут удалены только одноразовые задачи (не периодические)\n"
        "⚠️ Удаляются только задачи с прошлыми датами",
        reply_markup=get_delete_tasks_interval_keyboard()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("delete_tasks_"))
async def select_delete_interval(callback: CallbackQuery, state: FSMContext):
    """Выбор интервала для удаления"""
    interval = callback.data.split("_")[2]  # today, month, year, all
    interval_info = DELETE_INTERVALS.get(interval, {})
    interval_name = interval_info.get("name", interval)
    
    await callback.message.edit_text(
        f"⚠️ Вы уверены, что хотите удалить одноразовые задачи {interval_name}?\n\n"
        "Это действие нельзя отменить!",
        reply_markup=get_confirm_delete_tasks_keyboard(interval)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_tasks_"))
async def confirm_delete_tasks(callback: CallbackQuery, state: FSMContext):
    """Подтвержденное удаление задач"""
    try:
        interval = callback.data.split("_")[3]  # today, month, year, all
        
        user_id = callback.from_user.id
        now = local_now()
        today = local_today()
        start_date = None
        end_date = None
        interval_name = ""
        
        if interval == "today":
            # Все прошлые задачи с настоящего времени до 00:00 этих суток
            tasks = await task_service.get_tasks_by_date(
                user_id=user_id,
                task_date=today,
                show_completed=True
            )
            
            # Фильтруем только одноразовые задачи
            one_time_tasks = [t for t in tasks if t.get("periodicity") == "none"]
            
            # Фильтруем задачи по времени
            current_time = now.time()
            tasks_to_delete = filter_tasks_by_time(one_time_tasks, today, current_time)
            
            # Удаляем задачи
            deleted_count = 0
            for task_id in tasks_to_delete:
                success = await task_service.delete_task(task_id, user_id)
                if success:
                    deleted_count += 1
            
            interval_name = DELETE_INTERVALS["today"]["name"]
            
            if deleted_count > 0:
                await callback.message.edit_text(
                    f"✅ Удалено {deleted_count} одноразовых задач {interval_name}.",
                    reply_markup=get_main_menu()
                )
                await callback.answer(f"✅ Удалено {deleted_count} задач!")
            else:
                await callback.message.edit_text(
                    f"ℹ️ Не найдено одноразовых задач {interval_name} для удаления.",
                    reply_markup=get_main_menu()
                )
                await callback.answer("ℹ️ Задач не найдено")
            
            await state.clear()
            return
        elif interval in ("month", "year", "all"):
            interval_info = DELETE_INTERVALS[interval]
            interval_name = interval_info["name"]
            
            if interval == "all":
                start_date = None
                end_date = None
            else:
                end_date = today
                start_date = today - timedelta(days=interval_info["days"])
        else:
            await callback.answer("❌ Неверный интервал!", show_alert=True)
            return
        
        # Получаем все задачи в диапазоне дат
        tasks = await db.get_tasks_by_date_range(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )

        # Массовая очистка предназначена только для одноразовых задач.
        tasks = [task for task in tasks if task.get("periodicity") == "none"]
        
        # Фильтруем задачи по времени: удаляем только те, которые уже прошли
        current_time = now.time()
        tasks_to_delete = filter_tasks_by_time(tasks, today, current_time)
        
        # Удаляем отфильтрованные задачи списком
        deleted_count = await db.delete_tasks_by_ids(user_id, tasks_to_delete) if tasks_to_delete else 0
        
        if deleted_count > 0:
            await callback.message.edit_text(
                f"✅ Удалено {deleted_count} одноразовых задач {interval_name}.",
                reply_markup=get_main_menu()
            )
            await callback.answer(f"✅ Удалено {deleted_count} задач!")
        else:
            await callback.message.edit_text(
                f"ℹ️ Не найдено одноразовых задач {interval_name} для удаления.",
                reply_markup=get_main_menu()
            )
            await callback.answer("ℹ️ Задач не найдено")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при удалении задач: {e}", exc_info=True)
        await callback.message.edit_text(
            "❌ Ошибка сервера. Попробуйте позже.",
            reply_markup=get_main_menu()
        )
        await callback.answer("Ошибка!", show_alert=True)
