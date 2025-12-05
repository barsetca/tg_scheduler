"""Главный файл для запуска бота"""
import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from config import BOT_TOKEN, TIMEZONE
from database import db
from services.reminder_service import reminder_service
from services.task_service import task_service
from utils.keyboards import get_reminder_actions
from utils.formatting import format_reminder_message
from middleware.restart_check import RestartCheckMiddleware, set_start_time
from middleware.advanced_rate_limiter import AdvancedRateLimiterMiddleware

# Импорт обработчиков
from handlers import start, tasks, view, reminders, callbacks, calendar, time, cleanup

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def check_and_send_reminders(bot: Bot):
    """Проверка и отправка напоминаний"""
    logger.debug(f"⏰ Планировщик проверяет напоминания... (время: {datetime.now()})")
    try:
        due_reminders = await reminder_service.get_due_reminders()
        
        if not due_reminders:
            logger.debug("📭 Напоминаний для отправки не найдено")
            return
        
        logger.info(f"📬 Найдено {len(due_reminders)} напоминаний для отправки")
        
        for reminder in due_reminders:
            try:
                user_id = reminder["user_id"]
                task_id = reminder["task_id"]
                reminder_id = reminder["id"]
                reminder_datetime_str = reminder.get("reminder_datetime")
                
                logger.info(f"🔄 Обработка напоминания {reminder_id} для задачи {task_id} пользователя {user_id} (время: {reminder_datetime_str})")
                
                # Получаем задачу
                task = await task_service.get_task(task_id, user_id)
                if not task:
                    # Задача удалена, помечаем напоминание как отправленное
                    await reminder_service.mark_reminder_sent(reminder_id, user_id)
                    logger.info(f"⚠️ Задача {task_id} удалена, напоминание {reminder_id} помечено как отправленное")
                    continue
                
                # Если задача уже выполнена, помечаем напоминание как отправленное
                if task.get("is_completed"):
                    await reminder_service.mark_reminder_sent(reminder_id, user_id)
                    logger.info(f"ℹ️ Задача {task_id} уже выполнена, напоминание {reminder_id} помечено как отправленное (напоминание не отправлено)")
                    continue
                
                # Получаем время напоминания из задачи
                minutes_before = task.get("reminder_time", 0)
                
                # Отправляем напоминание
                message = format_reminder_message(task, minutes_before)
                
                logger.info(f"📤 Попытка отправить напоминание {reminder_id} пользователю {user_id} для задачи '{task.get('title', 'N/A')}'")
                
                try:
                    result = await bot.send_message(
                        chat_id=user_id,
                        text=message,
                        reply_markup=get_reminder_actions(task_id, reminder_id)
                    )
                    
                    # Отмечаем напоминание как отправленное только после успешной отправки
                    await reminder_service.mark_reminder_sent(reminder_id, user_id)
                    logger.info(f"✅ УСПЕШНО отправлено напоминание {reminder_id} для задачи {task_id} пользователю {user_id} (message_id: {result.message_id})")
                    
                except Exception as send_error:
                    # Обрабатываем ошибки отправки отдельно
                    error_str = str(send_error).lower()
                    error_type = type(send_error).__name__
                    
                    logger.error(f"❌ ОШИБКА отправки напоминания {reminder_id} пользователю {user_id}: {error_type}: {str(send_error)}", exc_info=True)
                    
                    # Критичные ошибки - помечаем как отправленное (не будем пытаться снова)
                    if ("bot was blocked" in error_str or "chat not found" in error_str or 
                        "user is deactivated" in error_str or "bot blocked by the user" in error_str or
                        "chat_id is empty" in error_str):
                        logger.warning(f"⚠️ Пользователь {user_id} заблокировал бота или чат не найден. Напоминание {reminder_id} помечено как отправленное.")
                        await reminder_service.mark_reminder_sent(reminder_id, user_id)
                    # Временные ошибки - не помечаем, попробуем еще раз
                    elif "rate limit" in error_str or "too many requests" in error_str or "flood" in error_str:
                        logger.warning(f"⏱️ Превышен лимит запросов для пользователя {user_id}. Напоминание {reminder_id} будет отправлено позже.")
                    else:
                        # Другие ошибки - логируем, но не помечаем как отправленное
                        logger.error(f"❌ НЕИЗВЕСТНАЯ ошибка при отправке напоминания {reminder_id} пользователю {user_id}: {error_type}: {str(send_error)}", exc_info=True)
                        # Не помечаем как отправленное - попробуем еще раз в следующий раз
                    
            except Exception as e:
                reminder_id = reminder.get("id", "unknown")
                user_id = reminder.get("user_id", "unknown")
                logger.error(f"❌ Критическая ошибка при обработке напоминания {reminder_id} для пользователя {user_id}: {e}", exc_info=True)
                # Не помечаем как отправленное при критических ошибках - попробуем еще раз
                    
    except Exception as e:
        logger.error(f"❌ Критическая ошибка при проверке напоминаний: {e}", exc_info=True)


async def main():
    """Главная функция"""
    # Инициализация бота
    bot = Bot(
        token=BOT_TOKEN,
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Инициализация диспетчера
    dp = Dispatcher()
    
    # Устанавливаем время запуска для проверки перезапуска
    set_start_time()
    
    # Регистрация middleware
    # AdvancedRateLimiter должен быть первым, чтобы ограничивать запросы до других проверок
    dp.message.middleware(AdvancedRateLimiterMiddleware())
    dp.callback_query.middleware(AdvancedRateLimiterMiddleware())
    
    # Middleware для проверки перезапуска
    dp.message.middleware(RestartCheckMiddleware())
    dp.callback_query.middleware(RestartCheckMiddleware())
    
    # Регистрация роутеров (важен порядок - более специфичные обработчики должны быть первыми)
    # Команды должны обрабатываться первыми, поэтому view.router с командами должен быть перед tasks.router
    # cleanup.router должен быть перед callbacks.router, чтобы перехватывать confirm_delete_tasks_
    dp.include_router(start.router)
    dp.include_router(view.router)  # Обрабатывает команды /tasksdate - должен быть перед tasks.router
    dp.include_router(tasks.router)  # Обрабатывает edit_time_ и другие специфичные callback
    dp.include_router(reminders.router)
    dp.include_router(cleanup.router)  # Обработчик удаления задач (должен быть перед callbacks)
    dp.include_router(callbacks.router)
    dp.include_router(calendar.router)
    dp.include_router(time.router)  # Обрабатывает time_* callback (должен быть после tasks, чтобы не перехватывать edit_time_)
    
    # Глобальный обработчик ошибок
    @dp.errors()
    async def error_handler(update, exception):
        """Глобальный обработчик ошибок"""
        logger.error(f"Необработанная ошибка: {exception}", exc_info=True)
        try:
            from aiogram.types import Update
            if isinstance(update, Update):
                if update.message:
                    await update.message.answer(
                        "⚠️ Программа временно недоступна.\n\n"
                        "Попробуйте позже или обратитесь к администратору."
                    )
                elif update.callback_query:
                    await update.callback_query.answer(
                        "⚠️ Программа временно недоступна. Попробуйте позже.",
                        show_alert=True
                    )
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {e}")
    
    # Инициализация базы данных
    await db.init_db()
    logger.info("База данных инициализирована")
    
    # Инициализация планировщика
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    
    # Добавляем задачу проверки напоминаний каждую минуту
    scheduler.add_job(
        check_and_send_reminders,
        trigger=IntervalTrigger(minutes=1),
        args=[bot],
        id="check_reminders",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info(f"✅ Планировщик запущен (timezone: {TIMEZONE}). Проверка напоминаний каждую минуту.")
    
    try:
        # Запуск бота
        logger.info("Бот запущен")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown()
        await bot.session.close()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Остановка бота по запросу пользователя")

