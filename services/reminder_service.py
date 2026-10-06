"""Сервис для работы с напоминаниями"""
import logging
from datetime import timedelta
from typing import List, Dict, Any, Optional
from database import db
from utils.datetime_utils import local_now

logger = logging.getLogger(__name__)


class ReminderService:
    """Сервис для управления напоминаниями"""
    
    @staticmethod
    async def get_due_reminders() -> List[Dict[str, Any]]:
        """Получить все напоминания, которые должны быть отправлены"""
        now = local_now()
        return await db.get_pending_reminders(now)
    
    @staticmethod
    async def mark_reminder_sent(reminder_id: int, user_id: int) -> bool:
        """Отметить напоминание как отправленное"""
        return await db.mark_reminder_sent(reminder_id, user_id)
    
    @staticmethod
    async def postpone_reminder(reminder_id: int, user_id: int, minutes: int) -> bool:
        """Отложить напоминание на указанное количество минут (с проверкой user_id)"""
        # Получаем напоминание с проверкой user_id
        reminder = await db.get_reminder_by_id(reminder_id, user_id)
        
        if not reminder:
            return False
        
        # Откладываем относительно момента нажатия. Если исходное
        # напоминание уже просрочено, прибавление к старому времени привело бы
        # к его немедленной повторной отправке.
        new_time = local_now() + timedelta(minutes=minutes)
        
        return await db.update_reminder_time(reminder_id, user_id, new_time)
    
    @staticmethod
    async def get_reminder_by_id(reminder_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить напоминание по ID с проверкой user_id"""
        return await db.get_reminder_by_id(reminder_id, user_id)


# Глобальный экземпляр сервиса
reminder_service = ReminderService()
