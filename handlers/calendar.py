"""Обработчики календаря"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from datetime import date, datetime, timedelta
from utils.keyboards import get_calendar_keyboard
from utils.navigation import save_navigation_state
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.callback_query(F.data.startswith("calendar_") | F.data.startswith("calendar_view_"))
async def handle_calendar(callback: CallbackQuery, state: FSMContext):
    """Обработка действий календаря"""
    try:
        parts = callback.data.split("_")
        # Определяем префикс (calendar или calendar_view)
        if len(parts) > 2 and parts[1] == "view":
            action = parts[2]
            prefix_offset = 1
        else:
            action = parts[1]
            prefix_offset = 0
        
        data = await state.get_data()
        calendar_context = data.get("calendar_context", "create")  # create, edit или view_tasks
        
        if action == "select":
            # Выбор даты
            year = int(parts[2 + prefix_offset])
            month = int(parts[3 + prefix_offset])
            day = int(parts[4 + prefix_offset])
            selected_date = date(year, month, day)
            
            # Проверяем, что дата не в прошлом (только для создания задач)
            if selected_date < date.today() and calendar_context != "view_tasks":
                await callback.answer("❌ Нельзя выбрать прошедшую дату!", show_alert=True)
                return
            
            # Сохраняем выбранную дату
            await state.update_data(task_date=selected_date)
            
            # В зависимости от контекста переходим к следующему шагу
            if calendar_context == "create":
                await state.set_state("TaskCreationStates:waiting_for_time")
                from utils.navigation import save_navigation_state
                await save_navigation_state(state, "TaskCreationStates:waiting_for_date")
                from utils.keyboards import get_time_keyboard
                await state.update_data(time_context="create", time_hours=12, time_minutes=0)
                await callback.message.edit_text(
                    f"✅ Дата выбрана: {selected_date.strftime('%d.%m.%Y')}\n\n"
                    "Выберите время или нажмите 'Пропустить':",
                    reply_markup=get_time_keyboard(hours=12, minutes=0, prefix="time_create")
                )
            elif calendar_context == "edit":
                task_id = data.get("task_id")
                from services.task_service import task_service
                from utils.formatting import format_task_message
                from utils.keyboards import get_task_menu
                
                await task_service.update_task(task_id, callback.from_user.id, task_date=selected_date)
                task = await task_service.get_task(task_id, callback.from_user.id)
                await callback.message.edit_text(
                    f"✅ Дата обновлена!\n\n{format_task_message(task)}",
                    reply_markup=get_task_menu(task_id, "back")
                )
                await state.clear()
            elif calendar_context == "view_tasks":
                # Просмотр задач на выбранную дату
                from services.task_service import task_service
                from utils.formatting import format_tasks_list
                from utils.keyboards import get_tasks_list_keyboard, get_date_filters
                from utils.navigation import save_navigation_state
                
                # Сохраняем состояние навигации
                await save_navigation_state(state, "main_menu")
                
                tasks = await task_service.get_tasks_by_date(
                    user_id=callback.from_user.id,
                    task_date=selected_date,
                    show_completed=True
                )
                
                # Сохраняем выбранную дату в состоянии для фильтров
                await state.update_data(selected_date=selected_date.isoformat())
                
                message_text = format_tasks_list(tasks, selected_date)
                
                # Показываем список задач, если они есть, иначе показываем фильтры
                if tasks:
                    keyboard = get_tasks_list_keyboard(tasks, "view_task", "back")
                    await callback.message.edit_text(
                        message_text,
                        reply_markup=keyboard
                    )
                else:
                    message_text += "\n\nВыберите фильтр:"
                    await callback.message.edit_text(
                        message_text,
                        reply_markup=get_date_filters("back")
                    )
            
            await callback.answer(f"✅ Выбрана дата: {selected_date.strftime('%d.%m.%Y')}")
            
        elif action == "today":
            # Быстрый выбор сегодня
            today = date.today()
            await state.update_data(task_date=today)
            
            if calendar_context == "create":
                await state.set_state("TaskCreationStates:waiting_for_time")
                from utils.navigation import save_navigation_state
                await save_navigation_state(state, "TaskCreationStates:waiting_for_date")
                from utils.keyboards import get_time_keyboard
                await state.update_data(time_context="create", time_hours=12, time_minutes=0)
                await callback.message.edit_text(
                    f"✅ Дата выбрана: {today.strftime('%d.%m.%Y')}\n\n"
                    "Выберите время или нажмите 'Пропустить':",
                    reply_markup=get_time_keyboard(hours=12, minutes=0, prefix="time_create")
                )
            elif calendar_context == "edit":
                task_id = data.get("task_id")
                from services.task_service import task_service
                from utils.formatting import format_task_message
                from utils.keyboards import get_task_menu
                
                await task_service.update_task(task_id, callback.from_user.id, task_date=today)
                task = await task_service.get_task(task_id, callback.from_user.id)
                await callback.message.edit_text(
                    f"✅ Дата обновлена!\n\n{format_task_message(task)}",
                    reply_markup=get_task_menu(task_id, "back")
                )
                await state.clear()
            elif calendar_context == "view_tasks":
                from services.task_service import task_service
                from utils.formatting import format_tasks_list
                from utils.keyboards import get_tasks_list_keyboard, get_date_filters
                from utils.navigation import save_navigation_state
                
                # Сохраняем состояние навигации
                await save_navigation_state(state, "main_menu")
                
                tasks = await task_service.get_tasks_by_date(
                    user_id=callback.from_user.id,
                    task_date=today,
                    show_completed=True
                )
                
                # Сохраняем выбранную дату в состоянии для фильтров
                await state.update_data(selected_date=today.isoformat())
                
                message_text = format_tasks_list(tasks, today)
                
                # Показываем список задач, если они есть, иначе показываем фильтры
                if tasks:
                    keyboard = get_tasks_list_keyboard(tasks, "view_task", "back")
                    await callback.message.edit_text(
                        message_text,
                        reply_markup=keyboard
                    )
                else:
                    message_text += "\n\nВыберите фильтр:"
                    await callback.message.edit_text(
                        message_text,
                        reply_markup=get_date_filters("back")
                    )
            
            await callback.answer(f"✅ Выбрана дата: {today.strftime('%d.%m.%Y')}")
            
        elif action == "tomorrow":
            # Быстрый выбор завтра
            tomorrow = date.today() + timedelta(days=1)
            await state.update_data(task_date=tomorrow)
            
            if calendar_context == "create":
                await state.set_state("TaskCreationStates:waiting_for_time")
                from utils.navigation import save_navigation_state
                await save_navigation_state(state, "TaskCreationStates:waiting_for_date")
                from utils.keyboards import get_time_keyboard
                await state.update_data(time_context="create", time_hours=12, time_minutes=0)
                await callback.message.edit_text(
                    f"✅ Дата выбрана: {tomorrow.strftime('%d.%m.%Y')}\n\n"
                    "Выберите время или нажмите 'Пропустить':",
                    reply_markup=get_time_keyboard(hours=12, minutes=0, prefix="time_create")
                )
            elif calendar_context == "edit":
                task_id = data.get("task_id")
                from services.task_service import task_service
                from utils.formatting import format_task_message
                from utils.keyboards import get_task_menu
                
                await task_service.update_task(task_id, callback.from_user.id, task_date=tomorrow)
                task = await task_service.get_task(task_id, callback.from_user.id)
                await callback.message.edit_text(
                    f"✅ Дата обновлена!\n\n{format_task_message(task)}",
                    reply_markup=get_task_menu(task_id, "back")
                )
                await state.clear()
            elif calendar_context == "view_tasks":
                from services.task_service import task_service
                from utils.formatting import format_tasks_list
                from utils.keyboards import get_tasks_list_keyboard, get_date_filters
                from utils.navigation import save_navigation_state
                
                # Сохраняем состояние навигации
                await save_navigation_state(state, "main_menu")
                
                tasks = await task_service.get_tasks_by_date(
                    user_id=callback.from_user.id,
                    task_date=tomorrow,
                    show_completed=True
                )
                
                # Сохраняем выбранную дату в состоянии для фильтров
                await state.update_data(selected_date=tomorrow.isoformat())
                
                message_text = format_tasks_list(tasks, tomorrow)
                
                # Показываем список задач, если они есть, иначе показываем фильтры
                if tasks:
                    keyboard = get_tasks_list_keyboard(tasks, "view_task", "back")
                    await callback.message.edit_text(
                        message_text,
                        reply_markup=keyboard
                    )
                else:
                    message_text += "\n\nВыберите фильтр:"
                    await callback.message.edit_text(
                        message_text,
                        reply_markup=get_date_filters("back")
                    )
            
            await callback.answer(f"✅ Выбрана дата: {tomorrow.strftime('%d.%m.%Y')}")
            
        elif action == "prev_month":
            # Предыдущий месяц
            year = int(parts[2 + prefix_offset])
            month = int(parts[3 + prefix_offset])
            if month == 1:
                month = 12
                year -= 1
            else:
                month -= 1
            
            selected_date = data.get("task_date")
            prefix = "calendar_view" if calendar_context == "view_tasks" else "calendar"
            await callback.message.edit_reply_markup(
                reply_markup=get_calendar_keyboard(year, month, selected_date, prefix)
            )
            await callback.answer()
            
        elif action == "next_month":
            # Следующий месяц
            year = int(parts[2 + prefix_offset])
            month = int(parts[3 + prefix_offset])
            if month == 12:
                month = 1
                year += 1
            else:
                month += 1
            
            selected_date = data.get("task_date")
            prefix = "calendar_view" if calendar_context == "view_tasks" else "calendar"
            await callback.message.edit_reply_markup(
                reply_markup=get_calendar_keyboard(year, month, selected_date, prefix)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Ошибка при обработке календаря: {e}")
        await callback.answer("❌ Ошибка при выборе даты")


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Игнорирование callback (для неактивных кнопок)"""
    await callback.answer()

