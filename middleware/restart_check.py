"""Middleware для проверки перезапуска сервера"""
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from datetime import datetime
from utils.keyboards import get_main_menu
import logging
import os

logger = logging.getLogger(__name__)

# Путь к файлу для хранения времени запуска
_START_TIME_FILE = "data/bot_start_time.txt"


def set_start_time():
    """Установить время запуска бота"""
    # Создаем директорию data если её нет
    os.makedirs("data", exist_ok=True)
    
    current_time = datetime.now()
    # Сохраняем время запуска в файл
    try:
        with open(_START_TIME_FILE, "w") as f:
            f.write(current_time.isoformat())
        logger.info(f"Время запуска бота установлено: {current_time}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении времени запуска: {e}")


def get_start_time() -> datetime:
    """Получить время последнего запуска из файла"""
    try:
        if os.path.exists(_START_TIME_FILE):
            with open(_START_TIME_FILE, "r") as f:
                time_str = f.read().strip()
                return datetime.fromisoformat(time_str)
    except Exception as e:
        logger.error(f"Ошибка при чтении времени запуска: {e}")
    return None


class RestartCheckMiddleware(BaseMiddleware):
    """Middleware для проверки перезапуска и очистки состояний"""
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        """Проверка перезапуска перед обработкой события"""
        from aiogram.fsm.context import FSMContext
        from handlers.start import get_start_keyboard
        
        # Получаем FSM context
        state: FSMContext = data.get("state")
        
        # Получаем текущее время запуска из файла
        current_start_time = get_start_time()
        
        if state and current_start_time:
            # Проверяем, есть ли сохраненное время последнего использования
            state_data = await state.get_data()
            last_used_str = state_data.get("_last_bot_start_time")
            
            # Если время последнего использования не совпадает с текущим временем запуска,
            # значит был перезапуск
            if last_used_str:
                try:
                    last_used = datetime.fromisoformat(last_used_str)
                    if last_used != current_start_time:
                        # Был перезапуск - очищаем состояние
                        await state.clear()
                        
                        # Отправляем сообщение о перезапуске
                        try:
                            if isinstance(event, Message):
                                await event.answer(
                                    "⚠️ Сервер был перезапущен.\n\n"
                                    "Ваша сессия была прервана. Пожалуйста, начните заново:",
                                    reply_markup=get_start_keyboard()
                                )
                                return
                            elif isinstance(event, CallbackQuery):
                                await event.message.edit_text(
                                    "⚠️ Сервер был перезапущен.\n\n"
                                    "Ваша сессия была прервана. Пожалуйста, начните заново:",
                                    reply_markup=get_start_keyboard()
                                )
                                await event.answer("⚠️ Сессия прервана")
                                return
                        except Exception as e:
                            logger.error(f"Ошибка при отправке сообщения о перезапуске: {e}")
                            # Продолжаем обработку, если не удалось отправить сообщение
                except (ValueError, TypeError) as e:
                    logger.error(f"Ошибка при сравнении времени запуска: {e}")
                    # Если не удалось распарсить, считаем что был перезапуск
                    await state.clear()
            # Если у пользователя нет сохраненного времени, но есть состояние FSM,
            # это может означать, что бот был перезапущен после того, как пользователь начал работу
            # В этом случае тоже нужно очистить состояние и показать кнопку старт
            elif state_data and len(state_data) > 0:
                # Есть состояние, но нет времени запуска - вероятно перезапуск
                await state.clear()
                try:
                    if isinstance(event, Message):
                        await event.answer(
                            "⚠️ Сервер был перезапущен.\n\n"
                            "Ваша сессия была прервана. Пожалуйста, начните заново:",
                            reply_markup=get_start_keyboard()
                        )
                        return
                    elif isinstance(event, CallbackQuery):
                        await event.message.edit_text(
                            "⚠️ Сервер был перезапущен.\n\n"
                            "Ваша сессия была прервана. Пожалуйста, начните заново:",
                            reply_markup=get_start_keyboard()
                        )
                        await event.answer("⚠️ Сессия прервана")
                        return
                except Exception as e:
                    logger.error(f"Ошибка при отправке сообщения о перезапуске: {e}")
        
        # Сохраняем время последнего запуска в состояние
        if state and current_start_time:
            await state.update_data(_last_bot_start_time=current_start_time.isoformat())
        
        # Продолжаем обработку
        return await handler(event, data)

