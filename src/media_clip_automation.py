import os
import time
import random
from datetime import datetime, timedelta, timezone
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import logging
from dotenv import load_dotenv
from googleapiclient.errors import HttpError
import traceback
from time import sleep
from google.oauth2 import service_account
from social_media_poster import post_to_social_media

load_dotenv(dotenv_path='config/.env')

# Set up logging
logging.basicConfig(filename='media_clip_automation.log', level=logging.INFO,
                    format='%(asctime)s %(levelname)s:%(message)s')
logging.getLogger().addHandler(logging.StreamHandler())  # Also log to the console

# Configuration
MONITOR_FOLDER = os.getenv('MONITOR_FOLDER', r'E:\DeVlogs\[3-MediaClipID]')
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', '.content calendar')
CALENDAR_ID = os.getenv('CALENDAR_ID')
CREDENTIALS_FILE = os.getenv('CREDENTIALS_FILE')
POSTING_HOURS_START = int(os.getenv('POSTING_HOURS_START', 0))
POSTING_HOURS_END = int(os.getenv('POSTING_HOURS_END', 24))
PLATFORMS = os.getenv('PLATFORMS', 'YouTube Shorts,X Post,Facebook Story,Instagram Reel').split(',')

def authenticate_google_services():
    try:
        logging.info(f"Attempting to authenticate with credentials file: {CREDENTIALS_FILE}")
        scope = ['https://www.googleapis.com/auth/calendar',
                 'https://spreadsheets.google.com/feeds',
                 'https://www.googleapis.com/auth/drive',
                 'https://www.googleapis.com/auth/calendar.events']
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
        client = gspread.authorize(creds)
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        drive_service = build('drive', 'v3', credentials=creds)
        calendar_service = build('calendar', 'v3', credentials=creds)
        logging.info("Successfully authenticated and accessed Google services.")
        return sheet, drive_service, calendar_service
    except Exception as e:
        logging.error(f"Failed to authenticate Google services: {str(e)}")
        raise

def retry_calendar_api(func):
    def wrapper(*args, **kwargs):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except HttpError as e:
                if e.resp.status in [403, 500, 503] and attempt < max_retries - 1:
                    sleep_time = 2 ** attempt
                    logging.warning(f"Attempt {attempt + 1} failed. Retrying in {sleep_time} seconds...")
                    sleep(sleep_time)
                else:
                    raise
    return wrapper

@retry_calendar_api
def get_next_available_date(calendar_service):
    now = datetime.now(timezone.utc).isoformat()
    logging.info(f"Fetching events from calendar: {CALENDAR_ID}")
    logging.info(f"Time range start (timeMin): {now}")
    events_result = calendar_service.events().list(
        calendarId=CALENDAR_ID,
        timeMin=now,
        maxResults=1,
        singleEvents=True
    ).execute()
    logging.info(f"Events fetched: {len(events_result.get('items', []))}")
    return datetime.now(timezone.utc).date()

def generate_random_time(date):
    hour = random.randint(POSTING_HOURS_START, POSTING_HOURS_END - 1)
    minute = random.randint(0, 59)
    local_timezone = timezone(timedelta(hours=-5))  # Adjust for your timezone (EST: UTC-5)
    return datetime.combine(date, datetime.min.time(), tzinfo=local_timezone) + timedelta(hours=hour, minutes=minute)

class MediaClipHandler(FileSystemEventHandler):
    def __init__(self, sheet, drive_service, calendar_service):
        self.sheet = sheet
        self.drive_service = drive_service
        self.calendar_service = calendar_service
        super().__init__()

    def on_created(self, event):
        if not event.is_directory and event.src_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
            logging.info(f"New video detected: {event.src_path}")
            self.process_new_video(event.src_path)

    def process_new_video(self, video_path):
        try:
            file_id = self.upload_to_drive(video_path)
            if file_id:
                self.schedule_video(file_id, video_path)
        except Exception as e:
            logging.error(f"An error occurred while processing the video: {e}")

    def upload_to_drive(self, video_path):
        try:
            file_metadata = {'name': os.path.basename(video_path)}
            media = MediaFileUpload(video_path, resumable=True)
            file = self.drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            logging.info(f"File uploaded to Drive. ID: {file.get('id')}")
            return file.get('id')
        except Exception as e:
            logging.error(f"Failed to upload {video_path} to Drive: {e}")
            return None

    def schedule_video(self, file_id, video_path):
        try:
            # Check if the video has already been processed
            records = self.sheet.get_all_records()
            for record in records:
                if record['File ID'] == file_id or record['Video File Name'] == os.path.basename(video_path):
                    logging.info(f"Video '{os.path.basename(video_path)}' has already been processed. Skipping...")
                    return  # Exit the function if the video is already in the sheet

            next_date = get_next_available_date(self.calendar_service)
            scheduled_datetime = generate_random_time(next_date)
            platform = random.choice(PLATFORMS)

            # Add to Google Sheet
            row = [os.path.basename(video_path), file_id, scheduled_datetime.strftime('%Y-%m-%d %H:%M'), platform]
            result = self.sheet.append_row(row)
            logging.info(f"Added row to Google Sheet: {row}")
            logging.info(f"Google Sheets API response: {result}")
            logging.info(f"Video '{os.path.basename(video_path)}' scheduled for {scheduled_datetime} on {platform}")

            # Create Calendar Event
            event = {
                'summary': f'Post video on {platform}',
                'description': f'Video file ID: {file_id}\nPath: {video_path}',
                'start': {
                    'dateTime': scheduled_datetime.isoformat(),
                    'timeZone': 'America/New_York',
                },
                'end': {
                    'dateTime': (scheduled_datetime + timedelta(minutes=15)).isoformat(),
                    'timeZone': 'America/New_York',
                },
            }

            event = self.calendar_service.events().insert(calendarId=CALENDAR_ID, body=event).execute()
            logging.info(f"Event created: {event.get('htmlLink')}")

            # Post to social media
            caption = f"Check out our latest video! #ContentCreator #{platform.replace(' ', '')}"
            try:
                post_to_social_media(video_path, platform, caption)
            except Exception as e:
                logging.error(f"Failed to post to social media: {str(e)}")
                # You might want to add some recovery or notification logic here

        except Exception as e:
            logging.error(f"Error in schedule_video: {str(e)}")
            raise

def main():
    try:
        print(f"MONITOR_FOLDER: {MONITOR_FOLDER}")
        print(f"GOOGLE_SHEET_NAME: {GOOGLE_SHEET_NAME}")
        print(f"CALENDAR_ID: {CALENDAR_ID}")
        print(f"CREDENTIALS_FILE: {CREDENTIALS_FILE}")
        print(f"POSTING_HOURS_START: {POSTING_HOURS_START}")
        print(f"POSTING_HOURS_END: {POSTING_HOURS_END}")
        print(f"PLATFORMS: {PLATFORMS}")
        
        sheet, drive_service, calendar_service = authenticate_google_services()
        
        event_handler = MediaClipHandler(sheet, drive_service, calendar_service)
        observer = Observer()
        observer.schedule(event_handler, path=MONITOR_FOLDER, recursive=False)
        observer.start()
        logging.info(f"Started monitoring folder: {MONITOR_FOLDER}")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    except Exception as e:
        logging.critical(f"Script failed: {e}")
        logging.critical(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    main()