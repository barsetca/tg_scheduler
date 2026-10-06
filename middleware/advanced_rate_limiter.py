"""Продвинутый Rate Limiter с 3 уровнями защиты"""
from typing import Callable, Dict, Any, Awaitable, Optional, Tuple
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from collections import defaultdict
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# ==================== КОНФИГУРАЦИЯ ====================

# Уровень 1: Лимиты на действие
ACTION_LIMITS = {
    "/start": (1, 5),          # 1 раз в 5 сек
    "/newtask": (5, 20),       # 5 раз в 20 сек
    "edit_task": (10, 60),     # 10 раз в минуту
    "delete_task": (10, 60),   # 10 раз в минуту
    "view_today": (10, 10),    # 10 раз в 10 сек
    "/tasksdate": (5, 10),     # 5 раз в 10 сек
    "/help": (10, 60),         # 10 раз в минуту
    "button_click": (5, 1),    # 5 раз в 1 сек
    "send_message": (3, 2),    # 3 раза в 2 сек
}

# Уровень 2: Блокировка
MAX_VIOLATIONS = 10  # Максимальное количество нарушений
VIOLATION_WINDOW = 3600  # Окно для нарушений (1 час в секундах)
BLOCK_DURATION = 300  # Длительность блокировки (5 минут в секундах)

# Уровень 3: DDoS защита
MAX_NEW_USERS_PER_IP_HOUR = 10  # Максимум новых пользователей с одного IP в час
MAX_NEW_USERS_PER_IP_DAY = 50   # Максимум новых пользователей с одного IP в день

# ==================== ХРАНИЛИЩА ====================

# Уровень 1: Запросы пользователей по действиям
_user_requests: Dict[Tuple[int, str], list] = defaultdict(list)

# Уровень 2: Нарушения и блокировки пользователей
_user_violations: Dict[int, list] = defaultdict(list)  # user_id -> список временных меток нарушений
_user_blocks: Dict[int, datetime] = {}  # user_id -> время разблокировки

# Уровень 3: Новые пользователи по IP
_ip_new_users_hour: Dict[str, list] = defaultdict(list)  # IP -> список временных меток
_ip_new_users_day: Dict[str, list] = defaultdict(list)   # IP -> список временных меток
_blocked_ips: set = set()  # Заблокированные IP


def get_user_ip(event: TelegramObject) -> Optional[str]:
    """Получить IP адрес пользователя"""
    # ПРИМЕЧАНИЕ: В Telegram Bot API через polling режим IP адрес пользователя недоступен напрямую
    # Для реализации DDoS защиты по IP (Уровень 3) необходимо:
    # 1. Использовать webhook режим вместо polling
    # 2. Или использовать прокси-сервер для получения IP адресов
    # 
    # В текущей реализации DDoS защита по IP оставлена как заглушка
    # Реальная защита будет работать при переходе на webhook режим
    
    # В polling режиме IP недоступен
    if isinstance(event, (Message, CallbackQuery)):
        return None
    return None


def check_ddos_protection(user_ip: Optional[str], user_id: int) -> Tuple[bool, Optional[str]]:
    """
    Проверка DDoS защиты по IP (Уровень 3)
    
    Примечание: В polling режиме IP недоступен, поэтому проверка не выполняется.
    Для работы необходимо использовать webhook режим.
    
    Returns:
        Tuple[bool, Optional[str]]: (is_blocked, reason)
    """
    if not user_ip:
        # IP недоступен - пропускаем проверку
        return False, None
    
    # Проверка на блокированный IP
    if user_ip in _blocked_ips:
        return True, "IP заблокирован"
    
    now = datetime.now()
    
    # Проверка новых пользователей за час
    hour_users = _ip_new_users_hour[user_ip]
    hour_users[:] = [
        ts for ts in hour_users
        if (now - ts).total_seconds() < 3600
    ]
    
    if len(hour_users) >= MAX_NEW_USERS_PER_IP_HOUR:
        _blocked_ips.add(user_ip)
        logger.warning(f"DDoS защита: IP {user_ip} заблокирован (превышен лимит новых пользователей в час)")
        # Здесь можно добавить отправку уведомления админу
        return True, "Превышен лимит новых пользователей с этого IP (10/час)"
    
    # Проверка новых пользователей за день
    day_users = _ip_new_users_day[user_ip]
    day_users[:] = [
        ts for ts in day_users
        if (now - ts).total_seconds() < 86400
    ]
    
    if len(day_users) >= MAX_NEW_USERS_PER_IP_DAY:
        _blocked_ips.add(user_ip)
        logger.warning(f"DDoS защита: IP {user_ip} заблокирован (превышен лимит новых пользователей в день)")
        # Здесь можно добавить отправку уведомления админу
        return True, "Превышен лимит новых пользователей с этого IP (50/день)"
    
    return False, None


def get_action_type(event: TelegramObject) -> Optional[str]:
    """Определить тип действия из события"""
    if isinstance(event, Message):
        text = event.text or ""
        if text.startswith("/start"):
            return "/start"
        elif text.startswith("/newtask"):
            return "/newtask"
        elif text.startswith("/tasksdate"):
            return "/tasksdate"
        elif text.startswith("/help"):
            return "/help"
        else:
            return "send_message"
    
    elif isinstance(event, CallbackQuery):
        data = event.data or ""
        if data.startswith("edit_task_"):
            return "edit_task"
        elif data.startswith("delete_task_"):
            return "delete_task"
        elif data == "tasks_today":
            return "view_today"
        else:
            return "button_click"
    
    return None


def is_user_blocked(user_id: int) -> Tuple[bool, Optional[datetime]]:
    """Проверить, заблокирован ли пользователь"""
    if user_id in _user_blocks:
        unblock_time = _user_blocks[user_id]
        if datetime.now() < unblock_time:
            return True, unblock_time
        else:
            # Время блокировки истекло
            del _user_blocks[user_id]
            return False, None
    return False, None


def record_violation(user_id: int):
    """Записать нарушение для пользователя"""
    now = datetime.now()
    violations = _user_violations[user_id]
    
    # Очищаем старые нарушения (старше VIOLATION_WINDOW)
    violations[:] = [
        v_time for v_time in violations
        if (now - v_time).total_seconds() < VIOLATION_WINDOW
    ]
    
    # Добавляем новое нарушение
    violations.append(now)
    
    # Проверяем, не превышен ли лимит нарушений
    if len(violations) >= MAX_VIOLATIONS:
        # Блокируем пользователя
        unblock_time = now + timedelta(seconds=BLOCK_DURATION)
        _user_blocks[user_id] = unblock_time
        logger.warning(f"Пользователь {user_id} заблокирован на {BLOCK_DURATION} секунд")
        return True
    
    return False


def check_action_limit(user_id: int, action: str) -> bool:
    """Проверить лимит для конкретного действия"""
    if action not in ACTION_LIMITS:
        return True  # Если лимита нет, разрешаем
    
    max_requests, time_window = ACTION_LIMITS[action]
    now = datetime.now()
    key = (user_id, action)
    
    # Очищаем старые запросы
    requests = _user_requests[key]
    requests[:] = [
        req_time for req_time in requests
        if (now - req_time).total_seconds() < time_window
    ]
    
    # Проверяем лимит
    if len(requests) >= max_requests:
        return False
    
    # Добавляем текущий запрос
    requests.append(now)
    return True


class AdvancedRateLimiterMiddleware(BaseMiddleware):
    """Продвинутый Rate Limiter с 3 уровнями защиты"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Обработка запроса с проверкой всех уровней защиты"""
        
        # Получаем user_id
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id if event.from_user else None
        
        if not user_id:
            return await handler(event, data)
        
        # Уровень 2: Проверка блокировки пользователя
        is_blocked, unblock_time = is_user_blocked(user_id)
        if is_blocked and unblock_time is not None:
            remaining_minutes = int((unblock_time - datetime.now()).total_seconds() / 60) + 1
            try:
                if isinstance(event, Message):
                    await event.answer(
                        f"⛔ Слишком много запросов. Попробуйте через {remaining_minutes} минут."
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        f"⛔ Слишком много запросов. Попробуйте через {remaining_minutes} минут.",
                        show_alert=True
                    )
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения о блокировке: {e}")
            return
        
        # Уровень 3: DDoS защита по IP (только если IP доступен)
        user_ip = get_user_ip(event)
        is_blocked_ddos, ddos_reason = check_ddos_protection(user_ip, user_id)
        if is_blocked_ddos:
            try:
                if isinstance(event, Message):
                    await event.answer(
                        f"⛔ Доступ ограничен: {ddos_reason}"
                    )
                elif isinstance(event, CallbackQuery):
                    await event.answer(
                        f"⛔ Доступ ограничен: {ddos_reason}",
                        show_alert=True
                    )
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения о DDoS блокировке: {e}")
            return
        
        # Определяем тип действия
        action = get_action_type(event)
        if not action:
            return await handler(event, data)
        
        # Уровень 1: Проверка лимита на действие
        if not check_action_limit(user_id, action):
            # Лимит превышен - записываем нарушение
            was_blocked = record_violation(user_id)
            
            if was_blocked:
                remaining_minutes = int(BLOCK_DURATION / 60)
                try:
                    if isinstance(event, Message):
                        await event.answer(
                            f"⛔ Слишком много запросов. Попробуйте через {remaining_minutes} минут."
                        )
                    elif isinstance(event, CallbackQuery):
                        await event.answer(
                            f"⛔ Слишком много запросов. Попробуйте через {remaining_minutes} минут.",
                            show_alert=True
                        )
                except Exception as e:
                    logger.error(f"Ошибка при отправке сообщения о блокировке: {e}")
            else:
                # Просто превышен лимит, но не заблокирован
                max_requests, time_window = ACTION_LIMITS.get(action, (1, 1))
                try:
                    if isinstance(event, Message):
                        await event.answer(
                            f"⏱️ Слишком много запросов для этого действия.\n\n"
                            f"Лимит: {max_requests} раз в {time_window} сек."
                        )
                    elif isinstance(event, CallbackQuery):
                        await event.answer(
                            f"⏱️ Слишком много запросов. Лимит: {max_requests} раз в {time_window} сек.",
                            show_alert=True
                        )
                except Exception as e:
                    logger.error(f"Ошибка при отправке сообщения о лимите: {e}")
            return
        
        # Все проверки пройдены, продолжаем обработку
        return await handler(event, data)

