"""Обработчики выбора времени"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import time, date
from utils.keyboards import get_time_keyboard
from utils.navigation import get_previous_state, save_navigation_state
from services.task_service import task_service
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("time_"))
async def handle_time_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора времени"""
    try:
        callback_data = callback.data
        parts = callback_data.split("_")
        
        # Определяем префикс и действие
        # Форматы: 
        # - time_hour_inc -> prefix="time", action="hour_inc", parts=['time', 'hour', 'inc']
        # - time_create_hour_inc -> prefix="time_create", action="hour_inc", parts=['time', 'create', 'hour', 'inc']
        # - time_edit_hour_inc -> prefix="time_edit", action="hour_inc", parts=['time', 'edit', 'hour', 'inc']
        # - time_create_quick_9_0 -> prefix="time_create", action="quick", parts=['time', 'create', 'quick', '9', '0']
        
        if len(parts) >= 3 and parts[1] in ["create", "edit"]:
            # Префикс типа time_create или time_edit
            prefix = f"{parts[0]}_{parts[1]}"  # time_create или time_edit
            # Действие начинается с parts[2]
            if len(parts) >= 4:
                # Проверяем, является ли parts[2] частью составного действия
                if parts[2] in ["hour", "min"]:
                    # Составное действие (hour_inc, hour_dec, min_inc, min_dec)
                    action = f"{parts[2]}_{parts[3]}"
                elif parts[2] == "quick":
                    # Быстрый выбор времени (quick_9_0)
                    action = "quick"
                else:
                    action = parts[2]
            else:
                action = parts[2]  # confirm, skip
            action_index = 2
        else:
            # Простой префикс time
            prefix = parts[0]  # time
            # Действие начинается с parts[1]
            if len(parts) >= 3:
                # Проверяем, является ли parts[1] частью составного действия
                if parts[1] in ["hour", "min"]:
                    # Составное действие (hour_inc, hour_dec, min_inc, min_dec)
                    action = f"{parts[1]}_{parts[2]}"
                elif parts[1] == "quick":
                    # Быстрый выбор времени (quick_9_0)
                    action = "quick"
                else:
                    action = parts[1]
            else:
                action = parts[1]  # confirm, skip
            action_index = 1
        
        data = await state.get_data()
        current_hours = data.get("time_hours", 12)
        current_minutes = data.get("time_minutes", 0)
        time_context = data.get("time_context", "create")  # create или edit
        
        if action == "hour_inc":
            # Увеличить часы
            current_hours = (current_hours + 1) % 24
            await state.update_data(time_hours=current_hours)
            await callback.message.edit_reply_markup(
                reply_markup=get_time_keyboard(current_hours, current_minutes, prefix)
            )
            await callback.answer()
            
        elif action == "hour_dec":
            # Уменьшить часы
            current_hours = (current_hours - 1) % 24
            await state.update_data(time_hours=current_hours)
            await callback.message.edit_reply_markup(
                reply_markup=get_time_keyboard(current_hours, current_minutes, prefix)
            )
            await callback.answer()
            
        elif action == "min_inc":
            # Увеличить минуты
            current_minutes = (current_minutes + 5) % 60
            await state.update_data(time_minutes=current_minutes)
            await callback.message.edit_reply_markup(
                reply_markup=get_time_keyboard(current_hours, current_minutes, prefix)
            )
            await callback.answer()
            
        elif action == "min_dec":
            # Уменьшить минуты
            current_minutes = (current_minutes - 5) % 60
            await state.update_data(time_minutes=current_minutes)
            await callback.message.edit_reply_markup(
                reply_markup=get_time_keyboard(current_hours, current_minutes, prefix)
            )
            await callback.answer()
            
        elif action == "quick" or action.startswith("quick"):
            # Быстрый выбор времени
            # Форматы: time_create_quick_9_0 -> parts=['time', 'create', 'quick', '9', '0'], action_index=2
            #          time_quick_9_0 -> parts=['time', 'quick', '9', '0'], action_index=1
            # Для time_create_quick_9_0: parts[3]='9', parts[4]='0'
            # Для time_quick_9_0: parts[2]='9', parts[3]='0'
            if len(parts) >= action_index + 3:
                hours = int(parts[action_index + 1])
                minutes = int(parts[action_index + 2])
            else:
                # Если формат неожиданный, используем значения по умолчанию
                hours = 12
                minutes = 0
            
            # Проверяем, не установлено ли уже это время
            if current_hours == hours and current_minutes == minutes:
                await callback.answer("ℹ️ Это время уже установлено", show_alert=False)
                return
            
            await state.update_data(time_hours=hours, time_minutes=minutes)
            await callback.message.edit_reply_markup(
                reply_markup=get_time_keyboard(hours, minutes, prefix)
            )
            await callback.answer()
            
        elif action == "confirm":
            # Подтверждение выбора времени
            selected_time = time(current_hours, current_minutes)
            
            if time_context == "create":
                # Проверка на дублирование времени при создании
                task_date = data.get("task_date", date.today())
                from database import db
                existing_tasks = await db.get_tasks_by_datetime(
                    user_id=callback.from_user.id,
                    task_date=task_date,
                    task_time=selected_time
                )
                
                if existing_tasks:
                    existing_task = existing_tasks[0]
                    task_time_str = selected_time.strftime('%H:%M')
                    existing_title = existing_task.get('title', 'Без названия')
                    await callback.message.edit_text(
                        f"⚠️ На это время ({task_time_str}) уже назначена задача:\n\n"
                        f"📋 {existing_title}\n\n"
                        f"Выберите другое время или измените предыдущую задачу:",
                        reply_markup=get_time_keyboard(current_hours, current_minutes, prefix)
                    )
                    await callback.answer(f"⚠️ На это время уже есть задача: {existing_title}", show_alert=True)
                    return
                
                await state.update_data(task_time=selected_time)
                
                # Показываем список задач на этот день
                from services.task_service import task_service
                from utils.formatting import format_time_str
                
                tasks = await task_service.get_tasks_by_date(
                    user_id=callback.from_user.id,
                    task_date=task_date,
                    show_completed=False
                )
                
                tasks_text = ""
                if tasks:
                    tasks_text = "\n\n📋 Задачи на этот день:\n"
                    for t in tasks:
                        task_time_str = format_time_str(t.get("task_time"))
                        if task_time_str:
                            tasks_text += f"  • {task_time_str} - {t.get('title', 'Без названия')}\n"
                        else:
                            tasks_text += f"  • Без времени - {t.get('title', 'Без названия')}\n"
                
                # При создании задачи переходим к выбору напоминания
                await state.set_state("TaskCreationStates:waiting_for_reminder")
                await save_navigation_state(state, "TaskCreationStates:waiting_for_time")
                from utils.keyboards import get_reminder_time_keyboard
                await callback.message.edit_text(
                    f"✅ Время установлено: {selected_time.strftime('%H:%M')}{tasks_text}\n\n"
                    "За сколько времени напомнить?",
                    reply_markup=get_reminder_time_keyboard("back")
                )
            elif time_context == "edit":
                # Проверка на дублирование времени при редактировании
                task_id = data.get("task_id")
                task = await task_service.get_task(task_id, callback.from_user.id)
                if task:
                    task_date_str = task.get("task_date")
                    if task_date_str:
                        from datetime import date as dt_date
                        task_date = dt_date.fromisoformat(task_date_str) if isinstance(task_date_str, str) else task_date_str
                        
                        from database import db
                        existing_tasks = await db.get_tasks_by_datetime(
                            user_id=callback.from_user.id,
                            task_date=task_date,
                            task_time=selected_time,
                            exclude_task_id=task_id
                        )
                        
                        if existing_tasks:
                            existing_task = existing_tasks[0]
                            task_time_str = selected_time.strftime('%H:%M')
                            existing_title = existing_task.get('title', 'Без названия')
                            await callback.message.edit_text(
                                f"⚠️ На это время ({task_time_str}) уже назначена задача:\n\n"
                                f"📋 {existing_title}\n\n"
                                f"Выберите другое время или измените предыдущую задачу:",
                                reply_markup=get_time_keyboard(current_hours, current_minutes, prefix)
                            )
                            await callback.answer(f"⚠️ На это время уже есть задача: {existing_title}", show_alert=True)
                            return
                
                # При редактировании обновляем задачу
                from services.task_service import task_service
                from utils.formatting import format_task_message
                from utils.keyboards import get_task_menu
                
                await task_service.update_task(
                    task_id, callback.from_user.id, task_time=selected_time
                )
                task = await task_service.get_task(task_id, callback.from_user.id)
                await callback.message.edit_text(
                    f"✅ Время обновлено!\n\n{format_task_message(task)}",
                    reply_markup=get_task_menu(task_id, "back")
                )
                await state.clear()
            
            await callback.answer(f"✅ Время установлено: {selected_time.strftime('%H:%M')}")
            
        elif action == "skip":
            # Пропустить установку времени
            await state.update_data(task_time=None)
            
            if time_context == "create":
                # При создании задачи переходим к выбору периодичности
                await state.update_data(reminder_time=0)
                await state.set_state("TaskCreationStates:waiting_for_periodicity")
                await save_navigation_state(state, "TaskCreationStates:waiting_for_time")
                from utils.keyboards import get_periodicity_keyboard
                await callback.message.edit_text(
                    "Время не установлено.\n\nПериодичность задачи:",
                    reply_markup=get_periodicity_keyboard("back")
                )
            elif time_context == "edit":
                # При редактировании обновляем задачу
                task_id = data.get("task_id")
                from services.task_service import task_service
                from utils.formatting import format_task_message
                from utils.keyboards import get_task_menu
                
                await task_service.update_task(
                    task_id, callback.from_user.id, task_time=None
                )
                task = await task_service.get_task(task_id, callback.from_user.id)
                await callback.message.edit_text(
                    f"✅ Время удалено!\n\n{format_task_message(task)}",
                    reply_markup=get_task_menu(task_id, "back")
                )
                await state.clear()
            
            await callback.answer("⏭️ Время пропущено")
            
    except Exception as e:
        logger.error(f"Ошибка при выборе времени: {e}")
        await callback.answer("❌ Ошибка при выборе времени")

