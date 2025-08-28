import json
import os
import sys
import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build


def get_agenda(student_id, begin, end, token):
    url = (f"https://web.spaggiari.eu/rest/v1/students/"
           f"{student_id}/agenda/all/{begin}/{end}")
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Auth-Token": token
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


def login(user_id, user_pass):
    url = "https://web.spaggiari.eu/rest/v1/auth/login"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10"
    }
    body = {
        "ident": None,
        "pass": user_pass,
        "uid": user_id
    }
    response = requests.post(url, headers=headers, data=json.dumps(body))
    if response.status_code == 200:
        return response.json()
    else:
        response.raise_for_status()


def sync_to_google_calendar(agenda, calendar_id, credentials_file):
    try:
        scopes = ["https://www.googleapis.com/auth/calendar"]
        credentials = service_account.Credentials.from_service_account_file(
            credentials_file, scopes=scopes
        )
        service = build("calendar", "v3", credentials=credentials)
        existing_events = []
        page_token = None

        while True:
            events = service.events().list(
                calendarId=calendar_id,
                pageToken=page_token
            ).execute()
            existing_events.extend(events.get('items', []))
            page_token = events.get('nextPageToken')
            if not page_token:
                break

        for event in agenda["agenda"]:
            if (not event["evtDatetimeBegin"] or
                not event["evtDatetimeEnd"] or
                    event["evtDatetimeBegin"] >= event["evtDatetimeEnd"]):
                continue

            for existing_event in existing_events:
                if existing_event['summary'] == event["notes"]:
                    ex_start = existing_event['start'].get(
                        'dateTime',
                        existing_event['start'].get('date')
                    )
                    ex_end = existing_event['end'].get(
                        'dateTime',
                        existing_event['end'].get('date')
                    )
                    if ex_start[:10] == event["evtDatetimeBegin"][:10]:
                        msg = (f"Rimuovo vecchio evento: "
                               f"{existing_event['summary']} - "
                               f"{ex_start} to {ex_end}")
                        print(msg)
                        service.events().delete(
                            calendarId=calendar_id,
                            eventId=existing_event['id']
                        ).execute()

            msg = (f"Aggiungo evento: {event['notes']} - "
                   f"{event['evtDatetimeBegin']} to "
                   f"{event['evtDatetimeEnd']}")
            print(msg)
            event_body = {
                "summary": event["notes"],
                "location": "",
                "description": (f"Prof: {event['authorName']}\n"
                                f"Descrizione: {event['notes']}"),
                "start": {
                    "dateTime": event["evtDatetimeBegin"],
                    "timeZone": "Europe/Rome",
                },
                "end": {
                    "dateTime": event["evtDatetimeEnd"],
                    "timeZone": "Europe/Rome",
                },
            }
            service.events().insert(
                calendarId=calendar_id,
                body=event_body
            ).execute()

        for existing_event in existing_events:
            event_in_agenda = any(
                (existing_event['summary'] == event["notes"] and
                 existing_event['start'].get(
                     'dateTime',
                     existing_event['start'].get('date')
                 ) == event["evtDatetimeBegin"] and
                 existing_event['end'].get(
                     'dateTime',
                     existing_event['end'].get('date')
                 ) == event["evtDatetimeEnd"])
                for event in agenda["agenda"]
            )
            if not event_in_agenda:
                start_time = existing_event['start'].get(
                    'dateTime',
                    existing_event['start'].get('date')
                )
                end_time = existing_event['end'].get(
                    'dateTime',
                    existing_event['end'].get('date')
                )
                msg = (f"Rimuovo evento eliminato da ClasseViva: "
                       f"{existing_event['summary']} - "
                       f"{start_time} to {end_time}")
                print(msg)
                service.events().delete(
                    calendarId=calendar_id,
                    eventId=existing_event['id']
                ).execute()

    except Exception as e:
        error_msg = ("Si è verificato un errore nel sincronizzare "
                     f"gli eventi con Google Calendar: {e}")
        print(error_msg)


def get_periods(student_id, z_auth_token, z_token):
    url = f"https://web.spaggiari.eu/rest/v1/students/{student_id}/periods"
    headers = {
        "Content-Type": "application/json",
        "Z-Dev-ApiKey": "Tg1NWEwNGIgIC0K",
        "User-Agent": "CVVS/std/4.1.7 Android/10",
        "Z-Auth-Token": z_auth_token,
        "Z-Token": z_token,
        "Z-Requested-With": "XMLHttpRequest",
        "Referer": ("https://web.spaggiari.eu/home/app/"
                    "default/menu_personale.php"),
        "Origin": "https://web.spaggiari.eu"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=4))
        return response.json()
    else:
        try:
            error_json = response.json()
            if (error_json.get("statusCode") == 422 and
                    "school year not started yet" in
                    error_json.get("error", "")):
                msg = ("\n[INFO] L'anno scolastico non è ancora iniziato. "
                       "Riprova quando sarà attivo nel registro "
                       "elettronico.\n")
                print(msg)
                return None
        except Exception:
            pass
        print("Request headers:")
        print(json.dumps(headers, indent=4))
        print("Response content:")
        print(response.text)
        response.raise_for_status()


def cli():
    """Entry point per l'applicazione CLI"""
    config_file = None

    # Controlla dove cercare i file di configurazione
    if os.path.isdir("/app"):
        config_file = "/app/config.json"
    else:
        config_file = "config.json"

    # Verifica se il file config.json esiste
    if not os.path.exists(config_file):
        print("❌ ERRORE: File config.json non trovato!")
        print(f"📍 Cercato in: {os.path.abspath(config_file)}")
        print("\n🔧 SOLUZIONE:")
        print("1. Assicurati di aver seguito le istruzioni di "
              "configurazione")
        print("2. Leggi la documentazione completa qui:")
        repo_url = ("   👉 https://github.com/LNLenost/CVVCalendarSync"
                    "#%EF%B8%8F-configurazione")
        print(repo_url)
        print("3. Crea il file config.json nella directory corrente")
        sys.exit(1)

    try:
        with open(config_file) as f:
            config = json.load(f)
    except json.JSONDecodeError:
        print("❌ ERRORE: Il file config.json non è un JSON valido!")
        print("🔧 SOLUZIONE: Controlla la sintassi del file config.json")
        repo_url = ("   👉 https://github.com/LNLenost/CVVCalendarSync"
                    "#%EF%B8%8F-configurazione")
        print(repo_url)
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERRORE: Impossibile leggere config.json: {e}")
        sys.exit(1)

    # Estrai le configurazioni
    user_id = config.get("user_id")
    user_pass = config.get("user_pass")
    calendar_id = config.get("calendar_id")
    credentials_file = config.get("credentials_file")

    # Valida le configurazioni richieste
    required_fields = [user_id, user_pass, calendar_id, credentials_file]
    if not all(required_fields):
        print("❌ ERRORE: Configurazione incompleta in config.json!")
        print("🔧 SOLUZIONE:")
        print("   Assicurati che config.json contenga tutti i campi "
              "richiesti:")
        print("   - user_id")
        print("   - user_pass")
        print("   - calendar_id")
        print("   - credentials_file")
        repo_url = ("   👉 https://github.com/LNLenost/CVVCalendarSync"
                    "#%EF%B8%8F-configurazione")
        print(repo_url)
        sys.exit(1)

    # Determina il percorso completo del file credenziali
    if os.path.isdir("/app"):
        credentials_file = "/app/" + credentials_file

    # Verifica se il file credentials.json esiste
    if not os.path.exists(credentials_file):
        print("❌ ERRORE: File credentials.json non trovato!")
        print(f"📍 Cercato in: {os.path.abspath(credentials_file)}")
        print("\n🔧 SOLUZIONE:")
        print("1. Scarica il file credentials.json da Google Cloud "
              "Console")
        print("2. Salvalo nella stessa directory di config.json")
        print("3. Leggi la guida completa qui:")
        repo_url = ("   👉 https://github.com/LNLenost/CVVCalendarSync"
                    "#2-scarica-credentialsjson")
        print(repo_url)
        sys.exit(1)

    student_id = "".join(filter(str.isdigit, user_id))

    try:
        login_response = login(user_id, user_pass)
        token = login_response.get("token")
        z_token = login_response.get("tokenAP")
        if not token or not z_token:
            print("login_response:")
            print(json.dumps(login_response, indent=4))
            raise ValueError("Token o tokenAP invalido!")

        full_name = (f"{login_response['firstName']} "
                     f"{login_response['lastName']}")
        print(f"Effettuato il login con il profilo {full_name}")

        periods = get_periods(student_id, token, z_token)
        if periods is None:
            sys.exit(1)

        period_start = periods["periods"][0]["dateStart"]
        period_end = periods["periods"][-1]["dateEnd"]
        period_start = period_start.replace("-", "")
        period_end = period_end.replace("-", "")

        agenda = get_agenda(student_id, period_start, period_end, token)
        sync_to_google_calendar(agenda, calendar_id, credentials_file)

    except requests.exceptions.RequestException as e:
        print(f"Si è verificato un errore: {e}")
    except Exception as e:
        print(f"Si è verificato un errore: {e}")


if __name__ == "__main__":
    cli()
