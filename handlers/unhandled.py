"""Обработчик необработанных сообщений"""
from aiogram import Router
from aiogram.types import Message
from utils.keyboards import get_main_menu
import logging

logger = logging.getLogger(__name__)

router = Router()


@router.message()
async def handle_unhandled_message(message: Message):
    """Обработчик необработанных сообщений (должен быть последним)"""
    # Показываем меню для всех сообщений, которые не обработаны другими роутерами
    # FSM состояния обрабатываются раньше благодаря порядку регистрации роутеров
    # Команды также обрабатываются раньше
    await message.answer(
        "❓ Для работы с ботом воспользуйтесь меню.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu()
    )

