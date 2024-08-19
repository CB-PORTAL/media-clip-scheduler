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

load_dotenv(dotenv_path='config/.env')  # This loads the variables from .env

# Print statements to confirm variables are loaded
print(f"MONITOR_FOLDER: {os.getenv('MONITOR_FOLDER')}")
print(f"GOOGLE_SHEET_NAME: {os.getenv('GOOGLE_SHEET_NAME')}")
print(f"CALENDAR_ID: {os.getenv('CALENDAR_ID')}")
print(f"CREDENTIALS_FILE: {os.getenv('CREDENTIALS_FILE')}")

# Set up logging
logging.basicConfig(filename='media_clip_automation.log', level=logging.INFO, 
                    format='%(asctime)s %(levelname)s:%(message)s')
logging.getLogger().addHandler(logging.StreamHandler())  # Also log to the console

def setup_logger():
    logger = logging.getLogger('MediaClipAutomation')
    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler('media_clip_automation.log')
    console_handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger

logger = setup_logger()

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
        scope = ['https://spreadsheets.google.com/feeds',
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
        
        # Test calendar access
        test_calendar_access(calendar_service)
        
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

def get_next_available_date(calendar_service):
    try:
        now = datetime.now(timezone.utc)
        logging.info(f"Fetching events from calendar: {CALENDAR_ID}")
        logging.info(f"Time range start: {now.isoformat()}")
        events_result = calendar_service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now.isoformat() + 'Z',
            maxResults=10,  # Reduced for testing
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        logging.info(f"Events fetched: {len(events_result.get('items', []))}")
        return now.date()  # For now, just return today's date
    except HttpError as e:
        logging.error(f"Calendar API error: {e.resp.status} {e.content.decode('utf-8')}")
        raise
    except Exception as e:
        logging.error(f"Unexpected error in get_next_available_date: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")
        raise

def test_calendar_access(calendar_service):
    try:
        now = datetime.now(timezone.utc)
        logging.info(f"Testing calendar access for: {CALENDAR_ID}")
        logging.info(f"Current time: {now.isoformat()}")
        events_result = calendar_service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=now.isoformat() + 'Z',
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        logging.info(f"Successfully fetched {len(events_result.get('items', []))} events")
    except HttpError as e:
        logging.error(f"Calendar API error: {e.resp.status} {e.content.decode('utf-8')}")
    except Exception as e:
        logging.error(f"Unexpected error in test_calendar_access: {str(e)}")
        logging.error(f"Traceback: {traceback.format_exc()}")

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
        except Exception as e:
            logging.error(f"Sheets API error: {str(e)}")
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

if __name__ == "__main__":
    main()