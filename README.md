# 🗓️ Jarvis Calendar Assistant (Google Calendar + TTS)

A Python script that connects to your **Google Calendar** and reads out your upcoming events using text-to-speech.  
It fetches events for the current week, next week, and the week after, and marks events happening soon as **URGENT**.

---

## ✨ Features

- 🔐 Uses the **Google Calendar API** (read-only)
- 📆 Reads events for:
  - This week
  - Next week
  - Week after next
- 🚨 Tags events within the next 2 days as **URGENT!**
- 🗣️ Uses **pyttsx3** for offline text-to-speech (no external TTS API)
- 🔊 Waits for audio output to be ready before speaking
- 🖥️ Prints a clean summary of events to the terminal as well

---

## 🛠 Tech Stack

- **Python 3**
- **Google Calendar API**
- [`google-auth-oauthlib`](https://pypi.org/project/google-auth-oauthlib/)
- [`google-api-python-client`](https://pypi.org/project/google-api-python-client/)
- [`pyttsx3`](https://pypi.org/project/pyttsx3/) for TTS
- [`sounddevice`](https://pypi.org/project/sounddevice/) for audio readiness checks

---

## 📁 Project Structure

```text
jarvis-calendar-assistant/
│
├── jarvis_tasks.py    # Main script (Google Calendar + TTS)
├── requirements.txt   # Python dependencies
├── .gitignore         # Excludes credentials/token files
└── README.md          # This file
