"""Работа с базой данных SQLite"""
import aiosqlite
import logging
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from config import DATABASE_PATH

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
    
    async def init_db(self):
        """Инициализация базы данных и создание таблиц"""
        async with aiosqlite.connect(self.db_path) as db:
            # Таблица задач
            await db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    created_date DATE DEFAULT CURRENT_DATE,
                    task_date DATE NOT NULL,
                    task_time TIME,
                    reminder_time INTEGER DEFAULT 0,
                    periodicity TEXT DEFAULT 'none',
                    is_completed BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Таблица напоминаний
            await db.execute("""
                CREATE TABLE IF NOT EXISTS reminders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    reminder_datetime DATETIME NOT NULL,
                    is_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """)
            
            # Таблица истории
            await db.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action TEXT,
                    action_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """)
            
            # Индексы для оптимизации
            await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_user_id ON tasks(user_id)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_tasks_date ON tasks(task_date)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_reminders_datetime ON reminders(reminder_datetime)")
            await db.execute("CREATE INDEX IF NOT EXISTS idx_reminders_sent ON reminders(is_sent)")
            
            await db.commit()
            logger.info("База данных инициализирована")
    
    async def create_task(
        self,
        user_id: int,
        title: str,
        task_date: date,
        description: Optional[str] = None,
        task_time: Optional[time] = None,
        reminder_time: int = 0,
        periodicity: str = "none"
    ) -> int:
        """Создать новую задачу"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO tasks (user_id, title, description, task_date, task_time, 
                                     reminder_time, periodicity)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (user_id, title, description, task_date.isoformat(), 
                      task_time.isoformat() if task_time else None, 
                      reminder_time, periodicity))
                await db.commit()
                task_id = cursor.lastrowid
                
                # Запись в историю
                await db.execute("""
                    INSERT INTO task_history (task_id, user_id, action)
                    VALUES (?, ?, ?)
                """, (task_id, user_id, "created"))
                await db.commit()
                
                logger.info(f"Создана задача {task_id} для пользователя {user_id}")
                return task_id
        except Exception as e:
            logger.error(f"Ошибка при создании задачи: {e}")
            raise
    
    async def get_task(self, task_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить задачу по ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT * FROM tasks 
                    WHERE id = ? AND user_id = ?
                """, (task_id, user_id)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            logger.error(f"Ошибка при получении задачи: {e}")
            raise
    
    async def update_task(
        self,
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
        try:
            updates = []
            params = []
            
            if title is not None:
                updates.append("title = ?")
                params.append(title)
            if description is not None:
                updates.append("description = ?")
                params.append(description)
            if task_date is not None:
                updates.append("task_date = ?")
                params.append(task_date.isoformat())
            if task_time is not None:
                updates.append("task_time = ?")
                params.append(task_time.isoformat() if task_time else None)
            if reminder_time is not None:
                updates.append("reminder_time = ?")
                params.append(reminder_time)
            if periodicity is not None:
                updates.append("periodicity = ?")
                params.append(periodicity)
            
            if not updates:
                return False
            
            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.extend([task_id, user_id])
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(f"""
                    UPDATE tasks 
                    SET {', '.join(updates)}
                    WHERE id = ? AND user_id = ?
                """, params)
                await db.commit()
                
                # Запись в историю
                await db.execute("""
                    INSERT INTO task_history (task_id, user_id, action)
                    VALUES (?, ?, ?)
                """, (task_id, user_id, "edited"))
                await db.commit()
                
                logger.info(f"Задача {task_id} обновлена")
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении задачи: {e}")
            raise
    
    async def complete_task(self, task_id: int, user_id: int) -> bool:
        """Отметить задачу как выполненную"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE tasks 
                    SET is_completed = TRUE, updated_at = ?
                    WHERE id = ? AND user_id = ?
                """, (datetime.now().isoformat(), task_id, user_id))
                await db.commit()
                
                # Запись в историю
                await db.execute("""
                    INSERT INTO task_history (task_id, user_id, action)
                    VALUES (?, ?, ?)
                """, (task_id, user_id, "completed"))
                await db.commit()
                
                # Удаляем все напоминания для этой задачи
                await db.execute("""
                    DELETE FROM reminders 
                    WHERE task_id = ? AND is_sent = FALSE
                """, (task_id,))
                await db.commit()
                
                logger.info(f"Задача {task_id} отмечена как выполненная")
                return True
        except Exception as e:
            logger.error(f"Ошибка при завершении задачи: {e}")
            raise
    
    async def delete_task(self, task_id: int, user_id: int) -> bool:
        """Удалить задачу"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Запись в историю перед удалением
                await db.execute("""
                    INSERT INTO task_history (task_id, user_id, action)
                    VALUES (?, ?, ?)
                """, (task_id, user_id, "deleted"))
                await db.commit()
                
                await db.execute("""
                    DELETE FROM tasks 
                    WHERE id = ? AND user_id = ?
                """, (task_id, user_id))
                await db.commit()
                
                logger.info(f"Задача {task_id} удалена")
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении задачи: {e}")
            raise
    
    async def get_tasks_by_date(
        self,
        user_id: int,
        task_date: date,
        show_completed: bool = True,
        show_overdue: bool = False
    ) -> List[Dict[str, Any]]:
        """Получить задачи на определенную дату"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                if show_overdue:
                    # Просроченные задачи (на прошлую дату и не завершены)
                    query = """
                        SELECT * FROM tasks 
                        WHERE user_id = ? AND task_date < ? AND is_completed = FALSE
                        ORDER BY task_time ASC, created_at ASC
                    """
                    params = (user_id, date.today().isoformat())
                else:
                    query = """
                        SELECT * FROM tasks 
                        WHERE user_id = ? AND task_date = ?
                    """
                    params = (user_id, task_date.isoformat())
                    
                    if not show_completed:
                        query += " AND is_completed = FALSE"
                    
                    query += " ORDER BY task_time ASC, created_at ASC"
                
                async with db.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении задач: {e}")
            raise
    
    async def get_tasks_by_datetime(
        self,
        user_id: int,
        task_date: date,
        task_time: time,
        exclude_task_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Получить задачи на определенную дату и время (для проверки дублирования)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                query = """
                    SELECT * FROM tasks 
                    WHERE user_id = ? AND task_date = ? AND task_time = ? AND is_completed = FALSE
                """
                params = [user_id, task_date.isoformat(), task_time.isoformat()]
                
                if exclude_task_id:
                    query += " AND id != ?"
                    params.append(exclude_task_id)
                
                query += " ORDER BY created_at ASC"
                
                async with db.execute(query, tuple(params)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении задач по дате и времени: {e}")
            raise
    
    async def get_tasks_by_date_range(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Получить все задачи в диапазоне дат с полными данными (включая task_time)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                query = """
                    SELECT * FROM tasks 
                    WHERE user_id = ?
                    AND periodicity = 'none'
                """
                params = [user_id]
                
                if start_date:
                    query += " AND task_date >= ?"
                    params.append(start_date.isoformat())
                
                if end_date:
                    query += " AND task_date <= ?"
                    params.append(end_date.isoformat())
                
                query += " ORDER BY task_date ASC, task_time ASC"
                
                async with db.execute(query, tuple(params)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении задач по диапазону: {e}")
            raise
    
    async def create_reminder(
        self,
        task_id: int,
        user_id: int,
        reminder_datetime: datetime
    ) -> int:
        """Создать напоминание"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO reminders (task_id, user_id, reminder_datetime)
                    VALUES (?, ?, ?)
                """, (task_id, user_id, reminder_datetime.isoformat()))
                await db.commit()
                reminder_id = cursor.lastrowid
                logger.info(f"Создано напоминание {reminder_id} для задачи {task_id}")
                return reminder_id
        except Exception as e:
            logger.error(f"Ошибка при создании напоминания: {e}")
            raise
    
    async def get_pending_reminders(self, before_datetime: datetime) -> List[Dict[str, Any]]:
        """Получить все неотправленные напоминания до указанного времени"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT r.*, t.title, t.description, t.task_time
                    FROM reminders r
                    JOIN tasks t ON r.task_id = t.id
                    WHERE r.is_sent = FALSE AND r.reminder_datetime <= ?
                    ORDER BY r.reminder_datetime ASC
                """, (before_datetime.isoformat(),)) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении напоминаний: {e}")
            raise
    
    async def mark_reminder_sent(self, reminder_id: int, user_id: int) -> bool:
        """Отметить напоминание как отправленное (с проверкой user_id)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    UPDATE reminders 
                    SET is_sent = TRUE 
                    WHERE id = ? AND user_id = ?
                """, (reminder_id, user_id))
                await db.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении напоминания: {e}")
            raise
    
    async def update_reminder_time(
        self,
        reminder_id: int,
        user_id: int,
        new_datetime: datetime
    ) -> bool:
        """Обновить время напоминания (с проверкой user_id)"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    UPDATE reminders 
                    SET reminder_datetime = ?, is_sent = FALSE
                    WHERE id = ? AND user_id = ?
                """, (new_datetime.isoformat(), reminder_id, user_id))
                await db.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Ошибка при обновлении времени напоминания: {e}")
            raise
    
    async def get_reminder_by_id(self, reminder_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить напоминание по ID с проверкой user_id"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("""
                    SELECT r.*, t.title, t.description, t.task_time
                    FROM reminders r
                    JOIN tasks t ON r.task_id = t.id
                    WHERE r.id = ? AND r.user_id = ?
                """, (reminder_id, user_id)) as cursor:
                    row = await cursor.fetchone()
                    if row:
                        return dict(row)
                    return None
        except Exception as e:
            logger.error(f"Ошибка при получении напоминания: {e}")
            raise
    
    async def delete_reminders_by_task(self, task_id: int) -> bool:
        """Удалить все напоминания для задачи"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    DELETE FROM reminders 
                    WHERE task_id = ?
                """, (task_id,))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении напоминаний: {e}")
            raise
    
    async def delete_one_time_tasks_by_date_range(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> int:
        """Удалить одноразовые задачи в интервале дат"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Сначала получаем ID задач для удаления напоминаний и записи в историю
                db.row_factory = aiosqlite.Row
                select_query = """
                    SELECT id FROM tasks 
                    WHERE user_id = ? 
                    AND periodicity = 'none'
                """
                select_params = [user_id]
                
                if start_date:
                    select_query += " AND task_date >= ?"
                    select_params.append(start_date.isoformat())
                
                if end_date:
                    select_query += " AND task_date <= ?"
                    select_params.append(end_date.isoformat())
                
                async with db.execute(select_query, tuple(select_params)) as cursor:
                    task_ids = [row[0] for row in await cursor.fetchall()]
                
                if not task_ids:
                    return 0
                
                # Удаляем напоминания для этих задач
                placeholders = ','.join(['?'] * len(task_ids))
                await db.execute(f"""
                    DELETE FROM reminders 
                    WHERE task_id IN ({placeholders})
                """, task_ids)
                
                # Записываем в историю перед удалением
                for task_id in task_ids:
                    await db.execute("""
                        INSERT INTO task_history (task_id, user_id, action)
                        VALUES (?, ?, ?)
                    """, (task_id, user_id, "deleted"))
                
                # Удаляем задачи
                delete_query = """
                    DELETE FROM tasks 
                    WHERE user_id = ? 
                    AND periodicity = 'none'
                """
                delete_params = [user_id]
                
                if start_date:
                    delete_query += " AND task_date >= ?"
                    delete_params.append(start_date.isoformat())
                
                if end_date:
                    delete_query += " AND task_date <= ?"
                    delete_params.append(end_date.isoformat())
                
                cursor = await db.execute(delete_query, tuple(delete_params))
                deleted_count = cursor.rowcount
                await db.commit()
                
                logger.info(f"Удалено {deleted_count} одноразовых задач для пользователя {user_id}")
                return deleted_count
        except Exception as e:
            logger.error(f"Ошибка при удалении задач: {e}")
            raise
    
    async def delete_tasks_by_ids(self, user_id: int, task_ids: List[int]) -> int:
        """Удалить задачи по списку ID"""
        if not task_ids:
            return 0
        
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Удаляем напоминания для этих задач
                placeholders = ','.join(['?'] * len(task_ids))
                await db.execute(f"""
                    DELETE FROM reminders 
                    WHERE task_id IN ({placeholders})
                """, task_ids)
                
                # Записываем в историю перед удалением
                for task_id in task_ids:
                    await db.execute("""
                        INSERT INTO task_history (task_id, user_id, action)
                        VALUES (?, ?, ?)
                    """, (task_id, user_id, "deleted"))
                
                # Удаляем задачи
                await db.execute(f"""
                    DELETE FROM tasks 
                    WHERE id IN ({placeholders})
                    AND user_id = ?
                """, (*task_ids, user_id))
                
                deleted_count = len(task_ids)
                await db.commit()
                
                logger.info(f"Удалено {deleted_count} задач по списку ID для пользователя {user_id}")
                return deleted_count
        except Exception as e:
            logger.error(f"Ошибка при удалении задач по списку ID: {e}")
            raise


# Глобальный экземпляр базы данных
db = Database()

