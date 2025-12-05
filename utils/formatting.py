"""Форматирование сообщений"""
from datetime import date, time, datetime
from typing import Optional, Dict, List
from utils.validators import parse_time, parse_date
from utils.constants import PERIODICITY_MAP


def format_task_message(task: Dict) -> str:
    """Форматирование сообщения о задаче"""
    status = "✅ Выполнено" if task.get("is_completed") else "⏳ В процессе"
    title = task.get("title", "Без названия")
    description = task.get("description", "")
    task_date = task.get("task_date", "")
    task_time = task.get("task_time", "")
    reminder_time = task.get("reminder_time", 0)
    periodicity = task.get("periodicity", "none")
    
    # Форматирование даты
    if task_date:
        try:
            date_obj = datetime.fromisoformat(task_date).date() if isinstance(task_date, str) else task_date
            today = date.today()
            if date_obj == today:
                date_str = "сегодня"
            elif date_obj == today.replace(day=today.day + 1):
                date_str = "завтра"
            else:
                date_str = date_obj.strftime("%d %B %Y")
        except:
            date_str = task_date
    else:
        date_str = "не указана"
    
    # Форматирование времени
    time_str = format_time_str(task_time)
    
    # Форматирование периодичности
    periodicity_str = PERIODICITY_MAP.get(periodicity, periodicity)
    
    message = f"📌 {title}\n"
    message += f"📊 Статус: {status}\n"
    
    if description:
        message += f"📝 Описание: {description}\n"
    
    message += f"📅 Дата: {date_str}\n"
    
    if time_str:
        message += f"⏰ Время: {time_str}\n"
    
    if reminder_time > 0:
        message += f"🔔 Напомнить за {reminder_time} мин\n"
    elif task_time:
        message += f"🔔 Напомнить в момент времени\n"
    
    message += f"🔄 Периодичность: {periodicity_str}\n"
    
    return message


def format_task_created_message(task: Dict) -> str:
    """Сообщение о создании задачи"""
    message = "✅ Задача добавлена!\n\n"
    message += format_task_message(task)
    return message


def format_reminder_message(task: Dict, minutes_before: int = 0) -> str:
    """Форматирование сообщения напоминания"""
    title = task.get("title", "Без названия")
    task_time = task.get("task_time", "")
    
    time_str = format_time_str(task_time)
    
    if minutes_before > 0:
        message = f"⏰ Через {minutes_before} минут!\n\n"
    else:
        message = "⏰ Время пришло!\n\n"
    
    message += f"📌 {title}\n"
    if time_str:
        message += f"⏱️ Время: {time_str}"
    
    return message


def format_tasks_list(tasks: List[Dict], date_obj: date) -> str:
    """Форматирование списка задач"""
    today = date.today()
    if date_obj == today:
        date_str = "сегодня"
    else:
        date_str = date_obj.strftime("%d %B %Y")
    
    message = f"📋 Ваши задачи на {date_str}\n\n"
    
    if not tasks:
        message += "Задач нет."
        return message
    
    completed_count = sum(1 for task in tasks if task.get("is_completed"))
    message += f"Всего: {len(tasks)} | Выполнено: {completed_count}\n\n"
    message += "Выберите задачу из списка ниже:"
    
    return message


def format_date(date_obj: date) -> str:
    """Форматирование даты для отображения"""
    today = date.today()
    if date_obj == today:
        return "сегодня"
    elif date_obj == today.replace(day=today.day + 1):
        return "завтра"
    else:
        return date_obj.strftime("%d %B %Y")


def format_time_str(time_value: str | time | None) -> str:
    """Форматирование времени в строку HH:MM"""
    if not time_value:
        return ""
    try:
        time_obj = parse_time(time_value)
        if time_obj:
            return time_obj.strftime("%H:%M")
        return ""
    except (ValueError, TypeError):
        if isinstance(time_value, str):
            return time_value[:5]  # HH:MM
        return str(time_value)

