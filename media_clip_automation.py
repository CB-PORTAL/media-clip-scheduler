import os
import time
import random
from datetime import datetime, timedelta
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Configuration
MONITOR_FOLDER = r'E:\DeVlogs\[3-MediaClipID]'
GOOGLE_SHEET_NAME = '.content calendar'
CALENDAR_ID = 'dc54840e5bf8249bfdf9c048174f4691814bd5a652298d25f5f5e80da966d51b@group.calendar.google.com'
CREDENTIALS_FILE = 'service_account_credentials.json'
POSTING_HOURS_START = 0
POSTING_HOURS_END = 24
PLATFORMS = ['YouTube Shorts', 'X Post', 'Facebook Story', 'Instagram Reel']

def authenticate_google_services():
    scope = ['https://spreadsheets.google.com/feeds',
             'https://www.googleapis.com/auth/drive',
             'https://www.googleapis.com/auth/calendar.events']
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    sheet = client.open(GOOGLE_SHEET_NAME).sheet1
    drive_service = build('drive', 'v3', credentials=creds)
    calendar_service = build('calendar', 'v3', credentials=creds)
    return sheet, drive_service, calendar_service

def get_next_available_date(calendar_service):
    now = datetime.utcnow()
    events_result = calendar_service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now.isoformat() + 'Z',
        maxResults=1000,
        singleEvents=True,
        orderBy='startTime'
    ).execute()
    events = events_result.get('items', [])

    next_available_day = now.date()
    while any(event['start'].get('date') == next_available_day.isoformat() for event in events):
        next_available_day += timedelta(days=1)
    return next_available_day

def generate_random_time(date):
    hour = random.randint(POSTING_HOURS_START, POSTING_HOURS_END - 1)
    minute = random.randint(0, 59)
    return datetime.combine(date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)

class MediaClipHandler(FileSystemEventHandler):
    def __init__(self, sheet, drive_service, calendar_service):
        self.sheet = sheet
        self.drive_service = drive_service
        self.calendar_service = calendar_service
        super().__init__()

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            print(f"New video detected: {event.src_path}")
            self.process_new_video(event.src_path)

    def process_new_video(self, video_path):
        try:
            file_id = self.upload_to_drive(video_path)
            if file_id:
                self.schedule_video(file_id, video_path)
        except Exception as e:
            print(f"An error occurred while processing the video: {e}")

    def upload_to_drive(self, video_path):
        file_metadata = {'name': os.path.basename(video_path)}
        media = MediaFileUpload(video_path, resumable=True)
        file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f"File uploaded to Drive. ID: {file.get('id')}")
        return file.get('id')

    def schedule_video(self, file_id, video_path):
        next_date = get_next_available_date(self.calendar_service)
        scheduled_datetime = generate_random_time(next_date)
        platform = random.choice(PLATFORMS)

        # Add to Google Sheet
        self.sheet.append_row([os.path.basename(video_path), file_id, scheduled_datetime.strftime('%Y-%m-%d %H:%M'), platform])

        # Create Calendar Event
        event = {
            'summary': f'Post video on {platform}',
            'description': f'Video file ID: {file_id}\nPath: {video_path}',
            'start': {
                'dateTime': scheduled_datetime.isoformat(),
                'timeZone': 'Your_Timezone',
            },
            'end': {
                'dateTime': (scheduled_datetime + timedelta(minutes=15)).isoformat(),
                'timeZone': 'Your_Timezone',
            },
        }

        event = self.calendar_service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")
        print(f"Scheduled '{os.path.basename(video_path)}' for {scheduled_datetime} on {platform}")

def main():
    sheet, drive_service, calendar_service = authenticate_google_services()
    print("Authenticated and accessed Google services.")

    event_handler = MediaClipHandler(sheet, drive_service, calendar_service)
    observer = Observer()
    observer.schedule(event_handler, path=MONITOR_FOLDER, recursive=False)
    observer.start()
    print(f"Started monitoring folder: {MONITOR_FOLDER}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()