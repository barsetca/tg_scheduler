"""Однократное получение OAuth refresh token для Google Calendar.

Запускайте на компьютере с браузером, а не на сервере без графической среды.
Клиент OAuth в Google Cloud должен быть типа "Desktop app".
"""
import os
import sys

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def main() -> None:
    load_dotenv()
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        print(
            "Заполните GOOGLE_OAUTH_CLIENT_ID и GOOGLE_OAUTH_CLIENT_SECRET в .env, "
            "затем повторите запуск.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    credentials = flow.run_local_server(
        host="localhost",
        port=0,
        open_browser=True,
        authorization_prompt_message="Откройте этот URL в браузере: {url}",
        success_message="Авторизация завершена. Можно закрыть эту вкладку.",
        access_type="offline",
        prompt="consent",
    )

    if not credentials.refresh_token:
        print(
            "Google не вернул refresh token. Отзовите доступ приложения в аккаунте Google "
            "и повторите авторизацию.",
            file=sys.stderr,
        )
        raise SystemExit(1)

    print("\nДобавьте в .env следующую строку:")
    print(f"GOOGLE_OAUTH_REFRESH_TOKEN={credentials.refresh_token}")
    print("\nНе публикуйте этот токен и не добавляйте .env в Git.")


if __name__ == "__main__":
    main()
