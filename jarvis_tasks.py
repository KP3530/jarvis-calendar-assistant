from __future__ import print_function
import datetime
import os.path
import pickle
import pyttsx3
import sounddevice as sd
import time
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ------------------ CONFIG ------------------
# Google Calendar API scope: read-only access to the user's calendar
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


# ------------------ AUDIO READY CHECK ------------------
def wait_for_audio(max_wait=15):
    """
    Block until the audio output device is ready or a timeout is reached.

    Args:
        max_wait (int): Maximum number of seconds to wait for a valid
                        audio output device before giving up.
    """
    ready = False
    start_time = time.time()

    # Keep trying until audio is ready or we exceed max_wait seconds
    while not ready and time.time() - start_time < max_wait:
        try:
            # Raises an exception if there is no valid output device
            sd.check_output_settings()
            ready = True
        except Exception:
            # Wait a bit and try again
            time.sleep(0.5)


# ------------------ GOOGLE AUTH ------------------
def authenticate_google():
    """
    Authenticate with Google using OAuth2 and return a Calendar API service.

    Uses 'token.pickle' to store and reuse credentials. If no valid token is
    found, or the token is expired, the OAuth flow is run using 'credentials.json'.

    Returns:
        googleapiclient.discovery.Resource: Authorized Calendar API service object.
    """
    creds = None

    # Load previously saved credentials (if they exist)
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If there are no valid credentials, start the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            # Refresh expired credentials
            creds.refresh(Request())
        else:
            # Run local server for user login and consent
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for next time
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    # Build a Calendar API service using the credentials
    service = build('calendar', 'v3', credentials=creds)
    return service


# ------------------ FETCH EVENTS ------------------
def get_events(service, start_date, end_date):
    """
    Fetch events from the primary Google Calendar between two datetimes.

    Args:
        service: Authorized Google Calendar API service.
        start_date (datetime): Start of the date range (inclusive).
        end_date (datetime): End of the date range (inclusive).

    Returns:
        list[dict]: List of event dictionaries returned by the API.
    """
    time_min = start_date.isoformat()
    time_max = end_date.isoformat()

    events_result = service.events().list(
        calendarId='primary',
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,       # Expand recurring events into individual instances
        orderBy='startTime'      # Sort events by start time
    ).execute()

    return events_result.get('items', [])


# ------------------ WEEKLY RANGES ------------------
def get_week_ranges():
    """
    Compute three week-long date ranges starting from the current week.

    Returns:
        list[tuple]: Each entry is (label, start_datetime, end_datetime), where:
            - label is a string ("This week", "Next week", "Week after next")
            - start_datetime and end_datetime are timezone-aware datetime objects
    """
    # Use UTC to align with the Calendar API
    today = datetime.datetime.now(datetime.timezone.utc)

    # End of the current week (Sunday) based on weekday (0 = Monday)
    end_of_week = today + datetime.timedelta(days=(6 - today.weekday()))

    # Next week: start one day after end_of_week, then 7-day block
    start_next = end_of_week + datetime.timedelta(days=1)
    end_next = start_next + datetime.timedelta(days=6)

    # Week after next: again, next 7-day block
    start_week_after = end_next + datetime.timedelta(days=1)
    end_week_after = start_week_after + datetime.timedelta(days=6)

    return [
        ("This week", today, end_of_week),
        ("Next week", start_next, end_next),
        ("Week after next", start_week_after, end_week_after)
    ]


# ------------------ GREETING ------------------
def get_greeting():
    """
    Return an appropriate greeting based on the current local time.

    Returns:
        str: "Good morning", "Good afternoon", or "Good evening"
    """
    hour = datetime.datetime.now().hour

    if 5 <= hour < 12:
        return "Good morning"
    elif 12 <= hour < 18:
        return "Good afternoon"
    else:
        return "Good evening"


# ------------------ FORMAT EVENTS ------------------
def format_events(events):
    """
    Transform raw event data into human-readable lines for speaking/printing.

    Events within the next 2 days are marked as URGENT.

    Args:
        events (list[dict]): List of event objects as returned by the Calendar API.

    Returns:
        list[str]: List of string messages describing each event.
    """
    if not events:
        return ["No events."]

    messages = []
    now = datetime.datetime.now(datetime.timezone.utc)

    for event in events:
        # Get the event start time (could be all-day 'date' or 'dateTime')
        start = event['start'].get('dateTime', event['start'].get('date'))

        try:
            # Normalize "Z" (Zulu/UTC) into +00:00 so fromisoformat can parse it
            start_dt = datetime.datetime.fromisoformat(start.replace("Z", "+00:00"))
            time_str = start_dt.strftime("%A at %I:%M %p")
        except Exception:
            # Fallback if parsing fails (e.g., all-day event date)
            start_dt = now  # avoid delta errors if we can't parse
            time_str = start

        # Compute time difference to decide if it's urgent
        delta = start_dt - now
        urgent = " (URGENT!)" if delta.days < 2 else ""

        summary = event.get('summary', 'Untitled event')
        messages.append(f"{summary} on {time_str}{urgent}")

    return messages


# ------------------ JARVIS SPEAK ------------------
def speak(text):
    """
    Use pyttsx3 to convert text to speech and play it through the default output.

    Args:
        text (str): The text to speak out loud.
    """
    engine = pyttsx3.init()

    # Set a comfortable speech rate (words per minute)
    engine.setProperty('rate', 175)

    # Try to select an English or male voice, if available
    voices = engine.getProperty('voices')
    for voice in voices:
        if "male" in voice.name.lower() or "english" in voice.name.lower():
            engine.setProperty('voice', voice.id)
            break

    engine.say(text)
    engine.runAndWait()


# ------------------ MAIN ------------------
def main():
    """
    Main entry point for the Jarvis Calendar Assistant.

    - Waits for audio readiness
    - Authenticates with Google Calendar
    - Retrieves events for the next three weeks
    - Prints them to the console
    - Reads them aloud using text-to-speech
    """
    # Ensure the audio device is ready before we start speaking
    wait_for_audio()

    # Authenticate and build the Calendar service
    service = authenticate_google()

    # Precompute the three weekly ranges
    week_ranges = get_week_ranges()

    # Greeting based on time of day
    greeting = get_greeting()

    # Startup Jarvis greeting
    welcome_message = f"{greeting}, sir. Here are your upcoming tasks for the next few weeks."
    print(welcome_message)
    speak(welcome_message)

    # Build a spoken/printed overview of the next three weeks
    jarvis_message = ""
    for week_name, start, end in week_ranges:
        events = get_events(service, start, end)
        event_text_list = format_events(events)

        # Format the section for this week
        week_text = f"{week_name}:\n" + "\n".join(event_text_list) + "\n"
        jarvis_message += week_text

        # Also print week summary to the console
        print(week_text)

    # Speak all events in one combined message
    speak(jarvis_message)


# ------------------ RUN SCRIPT ------------------
if __name__ == '__main__':
    main()
