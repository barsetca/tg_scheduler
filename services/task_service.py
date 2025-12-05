"""Сервис для работы с задачами"""
import logging
from datetime import date, time, datetime, timedelta
from typing import Optional, Dict, Any
from database import db

logger = logging.getLogger(__name__)


class TaskService:
    """Сервис для управления задачами"""
    
    @staticmethod
    async def create_task(
        user_id: int,
        title: str,
        task_date: date,
        description: Optional[str] = None,
        task_time: Optional[time] = None,
        reminder_time: int = 0,
        periodicity: str = "none"
    ) -> int:
        """Создать задачу"""
        task_id = await db.create_task(
            user_id=user_id,
            title=title,
            description=description,
            task_date=task_date,
            task_time=task_time,
            reminder_time=reminder_time,
            periodicity=periodicity
        )
        
        # Создаем напоминание, если указано время и время напоминания > 0
        if task_time and reminder_time > 0:
            await TaskService._create_reminder_for_task(
                task_id=task_id,
                user_id=user_id,
                task_date=task_date,
                task_time=task_time,
                reminder_time=reminder_time
            )
        
        return task_id
    
    @staticmethod
    async def _create_reminder_for_task(
        task_id: int,
        user_id: int,
        task_date: date,
        task_time: time,
        reminder_time: int
    ):
        """Создать напоминание для задачи"""
        # Вычисляем время напоминания
        task_datetime = datetime.combine(task_date, task_time)
        reminder_datetime = task_datetime - timedelta(minutes=reminder_time)
        
        # Если напоминание в будущем, создаем его
        if reminder_datetime > datetime.now():
            reminder_id = await db.create_reminder(
                task_id=task_id,
                user_id=user_id,
                reminder_datetime=reminder_datetime
            )
            logger.info(f"Создано напоминание {reminder_id} для задачи {task_id} пользователя {user_id} на {reminder_datetime}")
        else:
            logger.warning(f"Напоминание для задачи {task_id} в прошлом ({reminder_datetime}), не создано")
    
    @staticmethod
    async def get_task(task_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить задачу"""
        return await db.get_task(task_id, user_id)
    
    @staticmethod
    async def update_task(
        task_id: int,
        user_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        task_date: Optional[date] = None,
        task_time: Optional[time] = None,
        reminder_time: Optional[int] = None,
        periodicity: Optional[str] = None
    ) -> bool:
        """Обновить задачу"""
        # Получаем текущую задачу
        task = await db.get_task(task_id, user_id)
        if not task:
            return False
        
        # Обновляем задачу
        result = await db.update_task(
            task_id=task_id,
            user_id=user_id,
            title=title,
            description=description,
            task_date=task_date,
            task_time=task_time,
            reminder_time=reminder_time,
            periodicity=periodicity
        )
        
        # Если изменились дата, время или время напоминания, обновляем напоминания
        if result and (task_date or task_time or reminder_time is not None):
            # Удаляем старые напоминания
            await db.delete_reminders_by_task(task_id)
            
            # Создаем новое напоминание
            final_date = task_date if task_date else date.fromisoformat(task["task_date"])
            final_time = task_time if task_time else (
                time.fromisoformat(task["task_time"]) if task["task_time"] else None
            )
            final_reminder_time = reminder_time if reminder_time is not None else task["reminder_time"]
            
            # Создаем напоминание только если есть время и время напоминания > 0
            if final_time and final_reminder_time > 0:
                await TaskService._create_reminder_for_task(
                    task_id=task_id,
                    user_id=user_id,
                    task_date=final_date,
                    task_time=final_time,
                    reminder_time=final_reminder_time
                )
        
        return result
    
    @staticmethod
    async def complete_task(task_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Завершить задачу и создать следующую, если периодическая"""
        task = await db.get_task(task_id, user_id)
        if not task:
            return None
        
        # Отмечаем задачу как выполненную
        await db.complete_task(task_id, user_id)
        
        # Если задача периодическая, создаем следующую
        periodicity = task.get("periodicity", "none")
        if periodicity != "none":
            task_date_obj = date.fromisoformat(task["task_date"]) if isinstance(task["task_date"], str) else task["task_date"]
            task_time_obj = None
            if task.get("task_time"):
                task_time_obj = time.fromisoformat(task["task_time"]) if isinstance(task["task_time"], str) else task["task_time"]
            
            next_date, next_time = TaskService._calculate_next_period(
                task_date=task_date_obj,
                task_time=task_time_obj,
                periodicity=periodicity
            )
            
            if next_date:
                new_task_id = await TaskService.create_task(
                    user_id=user_id,
                    title=task["title"],
                    description=task.get("description"),
                    task_date=next_date,
                    task_time=next_time,
                    reminder_time=task.get("reminder_time", 0),
                    periodicity=periodicity
                )
                logger.info(f"Создана следующая периодическая задача {new_task_id} для задачи {task_id}")
        
        return task
    
    @staticmethod
    def _calculate_next_period(
        task_date: date,
        task_time: Optional[time],
        periodicity: str
    ) -> tuple:
        """Вычислить следующую дату и время для периодической задачи"""
        if periodicity == "hourly":
            if task_time:
                next_time = (datetime.combine(task_date, task_time) + timedelta(hours=1)).time()
                next_date = date.today()
                # Если время уже прошло сегодня, берем завтра
                if datetime.combine(next_date, next_time) < datetime.now():
                    next_date = next_date + timedelta(days=1)
                return next_date, next_time
        
        elif periodicity == "daily":
            next_date = date.today() + timedelta(days=1)
            return next_date, task_time
        
        elif periodicity == "weekly":
            next_date = date.today() + timedelta(days=7)
            return next_date, task_time
        
        elif periodicity == "monthly":
            next_date = date.today()
            # Добавляем месяц
            if next_date.month == 12:
                next_date = next_date.replace(year=next_date.year + 1, month=1)
            else:
                try:
                    next_date = next_date.replace(month=next_date.month + 1)
                except ValueError:
                    # Если день не существует в следующем месяце (например, 31 января -> февраль)
                    # Переходим на последний день следующего месяца
                    if next_date.month == 12:
                        next_date = date(next_date.year + 1, 1, 1)
                    else:
                        next_date = date(next_date.year, next_date.month + 1, 1)
            return next_date, task_time
        
        elif periodicity == "yearly":
            next_date = date.today().replace(year=date.today().year + 1)
            return next_date, task_time
        
        return None, None
    
    @staticmethod
    async def delete_task(task_id: int, user_id: int) -> bool:
        """Удалить задачу"""
        return await db.delete_task(task_id, user_id)
    
    @staticmethod
    async def get_tasks_by_date(
        user_id: int,
        task_date: date,
        show_completed: bool = True,
        show_overdue: bool = False
    ) -> list[Dict[str, Any]]:
        """Получить задачи на дату"""
        return await db.get_tasks_by_date(user_id, task_date, show_completed, show_overdue)


# Глобальный экземпляр сервиса
task_service = TaskService()

