"""Сервис для работы с задачами"""
import logging
from calendar import monthrange
from datetime import date, time, datetime, timedelta
from typing import Optional, Dict, Any
from database import UNSET, db
from utils.datetime_utils import local_now

logger = logging.getLogger(__name__)


class TaskValidationError(ValueError):
    """Ошибка проверки данных задачи, которую можно показать пользователю."""


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
        if periodicity == "none" and task_date < local_now().date():
            raise TaskValidationError("Одноразовую задачу нельзя создать задним числом.")

        task_id = await db.create_task(
            user_id=user_id,
            title=title,
            description=description,
            task_date=task_date,
            task_time=task_time,
            reminder_time=reminder_time,
            periodicity=periodicity
        )
        
        # Значение 0 означает напоминание точно в момент задачи; отрицательное
        # значение используется только для явной отмены напоминания.
        if task_time and reminder_time >= 0:
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
        if reminder_datetime > local_now():
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
        task_time: Optional[time] | object = UNSET,
        reminder_time: Optional[int] = None,
        periodicity: Optional[str] = None
    ) -> bool:
        """Обновить задачу"""
        # Получаем текущую задачу
        task = await db.get_task(task_id, user_id)
        if not task:
            return False

        # У периодической задачи нельзя оставлять очередное срабатывание в
        # прошлом. Иначе задача отображается как актуальная, но напоминание
        # для неё не создаётся в _create_reminder_for_task().
        is_time_update = task_time is not UNSET
        effective_task_date = task_date
        effective_task_time = task_time
        current_date = (
            date.fromisoformat(task["task_date"])
            if isinstance(task["task_date"], str)
            else task["task_date"]
        )
        current_time = (
            time.fromisoformat(task["task_time"])
            if isinstance(task.get("task_time"), str)
            else task.get("task_time")
        )
        final_date = task_date if task_date is not None else current_date
        final_time = task_time if is_time_update else current_time
        final_periodicity = periodicity if periodicity is not None else task.get("periodicity", "none")

        if final_periodicity == "none" and final_date < local_now().date():
            raise TaskValidationError("Одноразовую задачу нельзя перенести на прошедшую дату.")

        if (
            is_time_update
            and final_time is not None
            and final_periodicity != "none"
            and datetime.combine(final_date, final_time) <= local_now()
        ):
            effective_task_date, effective_task_time = TaskService._calculate_next_period(
                task_date=final_date,
                task_time=final_time,
                periodicity=final_periodicity,
            )
            logger.info(
                "Время периодической задачи %s уже прошло; следующее срабатывание перенесено на %s %s",
                task_id,
                effective_task_date,
                effective_task_time,
            )
        
        # Обновляем задачу
        result = await db.update_task(
            task_id=task_id,
            user_id=user_id,
            title=title,
            description=description,
            task_date=effective_task_date,
            task_time=effective_task_time,
            reminder_time=reminder_time,
            periodicity=periodicity
        )
        
        # Если изменились дата, время или время напоминания, обновляем напоминания
        if result and (effective_task_date is not None or is_time_update or reminder_time is not None):
            # Удаляем старые напоминания
            await db.delete_reminders_by_task(task_id)
            
            # Создаем новое напоминание
            final_date = effective_task_date if effective_task_date is not None else current_date
            final_time = effective_task_time if is_time_update else current_time
            final_reminder_time = reminder_time if reminder_time is not None else task["reminder_time"]
            
            # Ноль минут означает напоминание в момент задачи.
            if final_time and final_reminder_time >= 0:
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
        if periodicity == "hourly" and task_time:
            next_datetime = datetime.combine(task_date, task_time) + timedelta(hours=1)
            while next_datetime <= local_now():
                next_datetime += timedelta(hours=1)
            return next_datetime.date(), next_datetime.time()

        if periodicity == "daily":
            next_date = task_date + timedelta(days=1)
        elif periodicity == "weekly":
            next_date = task_date + timedelta(weeks=1)
        elif periodicity == "monthly":
            year = task_date.year + (task_date.month // 12)
            month = task_date.month % 12 + 1
            next_date = date(year, month, min(task_date.day, monthrange(year, month)[1]))
        elif periodicity == "yearly":
            year = task_date.year + 1
            next_date = date(year, task_date.month, min(task_date.day, monthrange(year, task_date.month)[1]))
        else:
            return None, None

        # Если задача давно просрочена, пропускаем уже прошедшие повторения.
        while datetime.combine(next_date, task_time or time.min) <= local_now():
            if periodicity == "daily":
                next_date += timedelta(days=1)
            elif periodicity == "weekly":
                next_date += timedelta(weeks=1)
            elif periodicity == "monthly":
                year = next_date.year + (next_date.month // 12)
                month = next_date.month % 12 + 1
                next_date = date(year, month, min(next_date.day, monthrange(year, month)[1]))
            else:  # yearly
                year = next_date.year + 1
                next_date = date(year, next_date.month, min(next_date.day, monthrange(year, next_date.month)[1]))

        return next_date, task_time
    
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
