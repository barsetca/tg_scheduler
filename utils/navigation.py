"""Утилиты для навигации с историей"""
from typing import Optional, List
from aiogram.fsm.context import FSMContext


async def save_navigation_state(state: FSMContext, current_state: str):
    """Сохранить текущее состояние в историю навигации"""
    data = await state.get_data()
    history: List[str] = data.get("nav_history", [])
    history.append(current_state)
    await state.update_data(nav_history=history)


async def get_previous_state(state: FSMContext) -> Optional[str]:
    """Получить предыдущее состояние из истории"""
    data = await state.get_data()
    history: List[str] = data.get("nav_history", [])
    if len(history) > 1:
        # Удаляем текущее состояние и возвращаем предыдущее
        history.pop()
        previous = history[-1] if history else None
        await state.update_data(nav_history=history)
        return previous
    return None


async def clear_navigation_history(state: FSMContext):
    """Очистить историю навигации"""
    await state.update_data(nav_history=[])


