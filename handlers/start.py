"""Обработчик команды /start и главного меню"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from utils.keyboards import get_main_menu
import logging

logger = logging.getLogger(__name__)

router = Router()


def get_start_keyboard():
    """Клавиатура для начала работы после перезапуска"""
    from utils.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Старт", callback_data="main_menu")]
    ])


@router.message(Command("start"))
async def cmd_start(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Привет! Я бот для управления ежедневными задачами.\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu()
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = """
ℹ️ **Помощь по использованию бота**

**Основные команды:**
/start - Главное меню
/newtask - Создать новую задачу
/tasksdate - Задачи по дате
/help - Эта справка

**Создание задачи:**
1. Нажмите "➕ Новая задача"
2. Введите описание
3. Выберите дату (по умолчанию - сегодня)
4. Укажите время (опционально)
5. Выберите время напоминания
6. Выберите периодичность

**Напоминания:**
- Бот напомнит вам о задаче в указанное время
- Можно отложить напоминание
- Можно сразу завершить или удалить задачу

**Периодические задачи:**
- После выполнения автоматически создается следующая задача
- Поддерживаются: каждый час, день, неделю, месяц, год

---
⚠️ **Важно:** Бот доступен только в часы работы локального сервера с 10:00 до 22:00 по времени Мадрида (CET/CEST).
"""
    await message.answer(help_text, reply_markup=get_main_menu())


@router.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "👋 Главное меню\n\nВыберите действие:",
        reply_markup=get_main_menu()
    )
    await callback.answer()


@router.callback_query(F.data == "help")
async def callback_help(callback: CallbackQuery):
    """Обработчик кнопки помощи"""
    help_text = """
ℹ️ **Помощь по использованию бота**

**Основные команды:**
/start - Главное меню
/newtask - Создать новую задачу
/tasksdate - Задачи по дате
/help - Эта справка

**Создание задачи:**
1. Нажмите "➕ Новая задача"
2. Введите описание
3. Выберите дату (по умолчанию - сегодня)
4. Укажите время (опционально)
5. Выберите время напоминания
6. Выберите периодичность

**Напоминания:**
- Бот напомнит вам о задаче в указанное время
- Можно отложить напоминание
- Можно сразу завершить или удалить задачу

**Периодические задачи:**
- После выполнения автоматически создается следующая задача
- Поддерживаются: каждый час, день, неделю, месяц, год

---
⚠️ **Важно:** Бот доступен только в часы работы локального сервера с 10:00 до 22:00 по времени Мадрида (CET/CEST).
"""
    await callback.message.edit_text(help_text, reply_markup=get_main_menu())
    await callback.answer()


@router.callback_query(F.data == "settings")
async def callback_settings(callback: CallbackQuery):
    """Обработчик настроек"""
    from utils.keyboards import InlineKeyboardMarkup, InlineKeyboardButton
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Удалить одноразовые задачи", callback_data="delete_one_time_tasks")],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data="back"),
            InlineKeyboardButton(text="🏠 Меню", callback_data="main_menu")
        ]
    ])
    await callback.message.edit_text(
        "⚙️ Настройки\n\n"
        "Выберите действие:",
        reply_markup=keyboard
    )
    await callback.answer()

