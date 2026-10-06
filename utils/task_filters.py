"""Утилиты для фильтрации задач"""
from datetime import date, time
from typing import List, Dict
from utils.validators import parse_date, parse_time


def filter_tasks_by_time(
    tasks: List[Dict],
    today: date,
    current_time: time
) -> List[int]:
    """
    Фильтрует задачи, которые уже прошли по времени.
    
    Возвращает список ID задач, которые должны быть удалены:
    - Задачи с датой в прошлом (до today) - удаляются все
    - Задачи на сегодня без времени - удаляются
    - Задачи на сегодня с прошедшим временем - удаляются
    - Задачи на сегодня с будущим временем - не удаляются
    - Задачи с будущей датой - не удаляются
    """
    tasks_to_delete = []
    
    for task in tasks:
        task_date_str = task.get("task_date")
        task_time_str = task.get("task_time")
        
        if not task_date_str:
            continue
        
        try:
            task_date_obj = parse_date(task_date_str)
        except (ValueError, TypeError):
            continue
        
        # Если дата в будущем - пропускаем (не удаляем)
        if task_date_obj > today:
            continue
        
        # Если дата в прошлом - удаляем все (независимо от времени)
        if task_date_obj < today:
            tasks_to_delete.append(task["id"])
            continue
        
        # Если дата = сегодня, проверяем время
        if task_date_obj == today:
            if not task_time_str:
                # Нет времени - удаляем (задача без времени считается прошедшей)
                tasks_to_delete.append(task["id"])
            else:
                # Есть время - проверяем, прошло ли оно
                try:
                    task_time_obj = parse_time(task_time_str)
                    if task_time_obj and task_time_obj <= current_time:
                        # Время уже прошло - удаляем
                        tasks_to_delete.append(task["id"])
                except (ValueError, TypeError):
                    # Если не удалось распарсить, считаем что время прошло
                    tasks_to_delete.append(task["id"])
    
    return tasks_to_delete











