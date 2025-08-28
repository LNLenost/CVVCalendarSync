"""
CVVCalendarSync - Sincronizza automaticamente eventi Classeviva con Google Calendar

Esempio di utilizzo come libreria:

```python
from cvvcalendarsync import login, get_agenda, sync_to_google_calendar

# Login
response = login("tuo_user_id", "tua_password")

# Ottieni agenda
agenda = get_agenda("11920234", "20250901", "20251231", response["token"])

# Sincronizza con Google Calendar
sync_to_google_calendar(agenda, "calendar_id@group.calendar.google.com", "credentials.json")
```

Esempio di utilizzo da CLI:

```bash
pip install cvvcalendarsync
cvvcalendarsync
```
"""

from .main import login, get_agenda, get_periods, sync_to_google_calendar, cli

__version__ = "0.1.0"
__all__ = ["login", "get_agenda", "get_periods", "sync_to_google_calendar", "cli"]
