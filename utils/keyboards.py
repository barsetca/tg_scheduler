"""Создание клавиатур для бота"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from typing import List, Dict
from datetime import date
from calendar import monthrange
from utils.datetime_utils import local_today


def get_main_menu() -> InlineKeyboardMarkup:
    """Главное меню"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Новая задача", callback_data="new_task")],
        [
            InlineKeyboardButton(text="📋 На сегодня", callback_data="tasks_today"),
            InlineKeyboardButton(text="📅 По дате", callback_data="tasks_date")
        ],
        [
            InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
        ],
        [InlineKeyboardButton(text="🗑️ Удалить одноразовые задачи", callback_data="delete_one_time_tasks")]
    ])
    return keyboard


def get_task_menu(task_id: int, back_callback: str = "back") -> InlineKeyboardMarkup:
    """Меню задачи"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_task_{task_id}")],
        [
            InlineKeyboardButton(text="✅ Завершить", callback_data=f"complete_task_{task_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_task_{task_id}")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback),
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
        ]
    ])
    return keyboard


def get_reminder_actions(task_id: int, reminder_id: int) -> InlineKeyboardMarkup:
    """Кнопки действий при напоминании"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏰ Отложить", callback_data=f"postpone_{reminder_id}_{task_id}"),
            InlineKeyboardButton(text="✅ Завершить", callback_data=f"complete_task_{task_id}")
        ],
        [
            InlineKeyboardButton(text="✅ ОК", callback_data=f"reminder_ok_{reminder_id}_{task_id}"),
            InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"delete_task_{task_id}")
        ]
    ])
    return keyboard


def get_reminder_time_keyboard(back_callback: str = "back") -> InlineKeyboardMarkup:
    """Выбор времени напоминания"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="0 мин", callback_data="reminder_0"),
            InlineKeyboardButton(text="5 мин", callback_data="reminder_5"),
            InlineKeyboardButton(text="15 мин", callback_data="reminder_15")
        ],
        [
            InlineKeyboardButton(text="30 мин", callback_data="reminder_30"),
            InlineKeyboardButton(text="60 мин", callback_data="reminder_60")
        ],
        [
            InlineKeyboardButton(text="За сутки", callback_data="reminder_1440"),
            InlineKeyboardButton(text="За неделю", callback_data="reminder_10080")
        ],
        [
            InlineKeyboardButton(text="❌ Отменить", callback_data="reminder_cancel"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback),
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
        ]
    ])
    return keyboard


def get_google_calendar_choice_keyboard() -> InlineKeyboardMarkup:
    """Выбор, нужно ли добавлять создаваемую задачу в Google Calendar."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📅 Добавить в Google Calendar", callback_data="google_calendar_yes"),
        ],
        [
            InlineKeyboardButton(text="Продолжить без календаря", callback_data="google_calendar_no"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="google_calendar_back"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu"),
        ],
    ])


def get_periodicity_keyboard(back_callback: str = "back") -> InlineKeyboardMarkup:
    """Выбор периодичности"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Нет (одноразовая)", callback_data="period_none")],
        [InlineKeyboardButton(text="Каждый час", callback_data="period_hourly")],
        [InlineKeyboardButton(text="Каждый день", callback_data="period_daily")],
        [InlineKeyboardButton(text="Каждую неделю", callback_data="period_weekly")],
        [InlineKeyboardButton(text="Каждый месяц", callback_data="period_monthly")],
        [InlineKeyboardButton(text="Каждый год", callback_data="period_yearly")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback),
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
        ]
    ])
    return keyboard


def get_date_filters(back_callback: str = "back") -> InlineKeyboardMarkup:
    """Фильтры для списка задач по дате"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Все", callback_data="filter_all"),
            InlineKeyboardButton(text="Выполненные", callback_data="filter_completed"),
            InlineKeyboardButton(text="Просроченные", callback_data="filter_overdue")
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback),
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
        ]
    ])
    return keyboard


def get_confirm_delete_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Подтверждение удаления"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_{task_id}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"view_task_{task_id}")
        ]
    ])
    return keyboard


def get_tasks_list_keyboard(tasks: List[Dict], prefix: str = "view_task", back_callback: str = "back") -> InlineKeyboardMarkup:
    """Клавиатура со списком задач (для редактирования)"""
    buttons = []
    for task in tasks:
        status = "☑" if task.get("is_completed") else "☐"
        time_str = task.get("task_time", "")
        if time_str:
            time_str = time_str[:5]  # HH:MM
        else:
            time_str = "Без времени"
        
        title = task.get('title', 'Без названия')
        # Ограничиваем длину названия для кнопки
        max_title_len = 28
        if len(title) > max_title_len:
            title = title[:max_title_len] + "..."
        
        periodicity = task.get("periodicity", "none")
        # Пометка периодической задачи
        periodicity_mark = " 🔄" if periodicity != "none" else ""
        
        # Формируем текст кнопки
        # ВАЖНО: Telegram API автоматически центрирует текст в inline кнопках
        # Это ограничение API и его нельзя обойти программно
        # Для максимального приближения к левому краю используем компактный формат
        # без лишних пробелов в начале и максимально длинный текст
        button_text = f"{status} {time_str} - {title}{periodicity_mark}"
        
        buttons.append([InlineKeyboardButton(
            text=button_text,
            callback_data=f"{prefix}_{task['id']}"
        )])
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback),
        InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_tasks_view_keyboard(back_callback: str = "back") -> InlineKeyboardMarkup:
    """Клавиатура для просмотра списка задач (с кнопкой Редактировать)"""
    buttons = [
        [InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_tasks_list")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback),
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_edit_task_keyboard(task_id: int, back_callback: str = None) -> InlineKeyboardMarkup:
    """Меню редактирования задачи"""
    if back_callback is None:
        back_callback = f"view_task_{task_id}"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Описание", callback_data=f"edit_title_{task_id}")],
        [InlineKeyboardButton(text="📅 Дата", callback_data=f"edit_date_{task_id}")],
        [InlineKeyboardButton(text="⏰ Время", callback_data=f"edit_time_{task_id}")],
        [InlineKeyboardButton(text="🔔 Напоминание", callback_data=f"edit_reminder_{task_id}")],
        [InlineKeyboardButton(text="🔄 Периодичность", callback_data=f"edit_periodicity_{task_id}")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback),
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
        ]
    ])
    return keyboard


def get_calendar_keyboard(year: int = None, month: int = None, selected_date: date = None, prefix: str = "calendar") -> InlineKeyboardMarkup:
    """Создать календарь для выбора даты"""
    if year is None or month is None:
        today = local_today()
        year = today.year
        month = today.month
    
    # Определяем, разрешены ли прошедшие даты (для просмотра задач)
    allow_past_dates = prefix.startswith("calendar_view")
    
    # Названия месяцев
    month_names = [
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
    ]
    
    # Получаем первый день месяца и количество дней
    first_day, num_days = monthrange(year, month)
    today = local_today()
    
    # Создаем кнопки календаря
    buttons = []
    
    # Заголовок с месяцем и годом, кнопки навигации
    buttons.append([
        InlineKeyboardButton(text="◀️", callback_data=f"{prefix}_prev_month_{year}_{month}"),
        InlineKeyboardButton(text=f"{month_names[month-1]} {year}", callback_data="ignore"),
        InlineKeyboardButton(text="▶️", callback_data=f"{prefix}_next_month_{year}_{month}")
    ])
    
    # Дни недели
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    buttons.append([
        InlineKeyboardButton(text=day, callback_data="ignore") for day in weekdays
    ])
    
    # Дни месяца
    week = []
    
    # Заполняем пустые ячейки до первого дня месяца
    for _ in range(first_day):
        week.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
    
    # Добавляем дни месяца
    for day in range(1, num_days + 1):
        current_day = date(year, month, day)
        
        # Определяем текст кнопки
        if current_day == today:
            text = f"•{day}•"  # Сегодня
        elif current_day < today:
            text = f"({day})"  # Прошлые даты
        else:
            text = str(day)  # Будущие даты
        
        # Если дата выбрана
        if selected_date and current_day == selected_date:
            text = f"[{day}]"
        
        # Для прошедших дат: делаем активными только если разрешены (для просмотра)
        if current_day < today and not allow_past_dates:
            callback = "ignore"
        else:
            callback = f"{prefix}_select_{year}_{month}_{day}"
        
        week.append(InlineKeyboardButton(text=text, callback_data=callback))
        
        # Если неделя заполнена, добавляем в buttons
        if len(week) == 7:
            buttons.append(week)
            week = []
    
    # Заполняем оставшиеся ячейки
    while len(week) < 7:
        week.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
    if week:
        buttons.append(week)
    
    # Кнопки быстрого выбора
    buttons.append([
        InlineKeyboardButton(text="📅 Сегодня", callback_data=f"{prefix}_today"),
        InlineKeyboardButton(text="📅 Завтра", callback_data=f"{prefix}_tomorrow")
    ])
    
    # Кнопки навигации
    buttons.append([
        InlineKeyboardButton(text="◀️ Назад", callback_data="back"),
        InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_time_keyboard(hours: int = 12, minutes: int = 0, prefix: str = "time") -> InlineKeyboardMarkup:
    """Клавиатура для выбора времени"""
    # Форматируем время для отображения
    time_str = f"{hours:02d}:{minutes:02d}"
    
    buttons = [
        # Отображение времени
        [InlineKeyboardButton(text=f"⏰ {time_str}", callback_data="ignore")],
        # Стрелки для часов
        [
            InlineKeyboardButton(text="◀️", callback_data=f"{prefix}_hour_dec"),
            InlineKeyboardButton(text="Часы", callback_data="ignore"),
            InlineKeyboardButton(text="▶️", callback_data=f"{prefix}_hour_inc")
        ],
        # Стрелки для минут
        [
            InlineKeyboardButton(text="◀️", callback_data=f"{prefix}_min_dec"),
            InlineKeyboardButton(text="Минуты", callback_data="ignore"),
            InlineKeyboardButton(text="▶️", callback_data=f"{prefix}_min_inc")
        ],
        # Быстрый выбор времени
        [
            InlineKeyboardButton(text="09:00", callback_data=f"{prefix}_quick_9_0"),
            InlineKeyboardButton(text="12:00", callback_data=f"{prefix}_quick_12_0"),
            InlineKeyboardButton(text="18:00", callback_data=f"{prefix}_quick_18_0")
        ],
        # Кнопки действий
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"{prefix}_confirm"),
            InlineKeyboardButton(text="⏭️ Пропустить", callback_data=f"{prefix}_skip")
        ],
        # Навигация
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_delete_tasks_interval_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора интервала удаления одноразовых задач"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 За сегодня", callback_data="delete_tasks_today")],
        [InlineKeyboardButton(text="📅 За последние 30 дней", callback_data="delete_tasks_month")],
        [InlineKeyboardButton(text="📅 За последние 12 месяцев", callback_data="delete_tasks_year")],
        [InlineKeyboardButton(text="🗑️ Все одноразовые задачи", callback_data="delete_tasks_all")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
        ]
    ])
    return keyboard


def get_confirm_delete_tasks_keyboard(interval: str) -> InlineKeyboardMarkup:
    """Подтверждение удаления задач"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"confirm_delete_tasks_{interval}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="delete_one_time_tasks")
        ]
    ])
    return keyboard
