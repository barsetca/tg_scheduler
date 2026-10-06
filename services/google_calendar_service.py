"""Асинхронная обёртка над Google Calendar API."""
import asyncio
import logging
from datetime import date, datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from config import (
    GOOGLE_CALENDAR_ENABLED,
    GOOGLE_CALENDAR_EVENT_DURATION_MINUTES,
    GOOGLE_CALENDAR_ID,
    GOOGLE_OAUTH_CLIENT_ID,
    GOOGLE_OAUTH_CLIENT_SECRET,
    GOOGLE_OAUTH_REFRESH_TOKEN,
    TIMEZONE,
)

logger = logging.getLogger(__name__)

GOOGLE_CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar.events"


class GoogleCalendarError(RuntimeError):
    """Ошибка конфигурации или вызова Google Calendar API."""


class GoogleCalendarService:
    """Создаёт события в календаре, заданном в конфигурации бота."""

    @staticmethod
    def is_configured() -> bool:
        return GOOGLE_CALENDAR_ENABLED and all(
            (GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_OAUTH_REFRESH_TOKEN)
        )

    @staticmethod
    def _build_event(
        title: str,
        task_date: date,
        task_time: time,
        description: Optional[str],
        reminder_time: int,
        periodicity: str,
    ) -> dict:
        timezone = ZoneInfo(TIMEZONE)
        start = datetime.combine(task_date, task_time, tzinfo=timezone)
        end = start + timedelta(minutes=GOOGLE_CALENDAR_EVENT_DURATION_MINUTES)
        event = {
            "summary": title,
            "description": description or "",
            "start": {"dateTime": start.isoformat(), "timeZone": TIMEZONE},
            "end": {"dateTime": end.isoformat(), "timeZone": TIMEZONE},
            "reminders": {"useDefault": False, "overrides": []},
        }

        recurrence = {
            "hourly": "HOURLY",
            "daily": "DAILY",
            "weekly": "WEEKLY",
            "monthly": "MONTHLY",
            "yearly": "YEARLY",
        }.get(periodicity)
        if recurrence:
            event["recurrence"] = [f"RRULE:FREQ={recurrence}"]

        if reminder_time >= 0:
            event["reminders"]["overrides"] = [
                {"method": "popup", "minutes": reminder_time}
            ]
        return event

    @staticmethod
    def _insert_event(event: dict) -> str:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError

        credentials = Credentials(
            token=None,
            refresh_token=GOOGLE_OAUTH_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_OAUTH_CLIENT_ID,
            client_secret=GOOGLE_OAUTH_CLIENT_SECRET,
            scopes=[GOOGLE_CALENDAR_SCOPE],
        )
        try:
            service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
            created_event = service.events().insert(
                calendarId=GOOGLE_CALENDAR_ID,
                body=event,
            ).execute()
            return created_event["id"]
        except HttpError as error:
            raise GoogleCalendarError(f"Google Calendar API: {error}") from error
        except Exception as error:
            raise GoogleCalendarError(f"Не удалось подключиться к Google Calendar: {error}") from error

    async def create_event(
        self,
        title: str,
        task_date: date,
        task_time: Optional[time],
        description: Optional[str],
        reminder_time: int,
        periodicity: str,
    ) -> str:
        if not self.is_configured():
            raise GoogleCalendarError("Google Calendar не настроен. Проверьте переменные GOOGLE_* в .env.")
        if task_time is None:
            raise GoogleCalendarError("Для добавления в Google Calendar необходимо указать время задачи.")

        event = self._build_event(
            title, task_date, task_time, description, reminder_time, periodicity
        )
        event_id = await asyncio.to_thread(self._insert_event, event)
        logger.info("Создано событие Google Calendar %s для задачи '%s'", event_id, title)
        return event_id


google_calendar_service = GoogleCalendarService()
