import os
import requests
import facebook
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tweepy
import logging
from dotenv import load_dotenv
import time

load_dotenv(dotenv_path='config/.env')

def retry_with_backoff(func, max_retries=3, initial_delay=1):
    def wrapper(*args, **kwargs):
        delay = initial_delay
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                logging.warning(f"Attempt {attempt + 1} failed. Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2
    return wrapper

@retry_with_backoff
def post_to_instagram(file_path, caption):
    access_token = os.getenv('INSTAGRAM_ACCESS_TOKEN')
    url = f'https://graph.facebook.com/v12.0/me/media'
    
    with open(file_path, 'rb') as video_file:
        payload = {
            'access_token': access_token,
            'caption': caption
        }
        files = {
            'video': video_file
        }
        response = requests.post(url, data=payload, files=files)
    
    if response.status_code == 200:
        logging.info("Successfully posted to Instagram.")
    else:
        logging.error(f"Failed to post to Instagram: {response.text}")
        raise Exception("Instagram posting failed")

@retry_with_backoff
def post_to_facebook(file_path, caption):
    access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
    graph = facebook.GraphAPI(access_token)
    
    with open(file_path, 'rb') as video_file:
        graph.put_video(video_file, caption=caption)
    
    logging.info("Successfully posted to Facebook.")

@retry_with_backoff
def post_to_youtube(file_path, title, description):
    client_id = os.getenv('YOUTUBE_CLIENT_ID')
    client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
    refresh_token = os.getenv('YOUTUBE_REFRESH_TOKEN')
    
    credentials = Credentials.from_authorized_user_info(
        {'client_id': client_id, 'client_secret': client_secret, 'refresh_token': refresh_token},
        ['https://www.googleapis.com/auth/youtube.upload']
    )
    
    youtube = build('youtube', 'v3', credentials=credentials)
    
    request_body = {
        'snippet': {
            'title': title,
            'description': description,
            'categoryId': '22'  # People & Blogs category
        },
        'status': {
            'privacyStatus': 'public'
        }
    }
    
    media = MediaFileUpload(file_path, chunksize=-1, resumable=True)
    
    response = youtube.videos().insert(
        part='snippet,status',
        body=request_body,
        media_body=media
    ).execute()
    
    logging.info(f"Successfully posted to YouTube. Video ID: {response['id']}")

@retry_with_backoff
def post_to_twitter(file_path, tweet_text):
    auth = tweepy.OAuthHandler(
        os.getenv('TWITTER_API_KEY'),
        os.getenv('TWITTER_API_SECRET')
    )
    auth.set_access_token(
        os.getenv('TWITTER_ACCESS_TOKEN'),
        os.getenv('TWITTER_ACCESS_TOKEN_SECRET')
    )
    
    api = tweepy.API(auth)
    
    media = api.media_upload(file_path)
    api.update_status(status=tweet_text, media_ids=[media.media_id])
    
    logging.info("Successfully posted to Twitter.")

def post_to_social_media(file_path, platform, caption):
    try:
        if platform == 'Instagram Reel':
            post_to_instagram(file_path, caption)
        elif platform == 'Facebook Story':
            post_to_facebook(file_path, caption)
        elif platform == 'YouTube Shorts':
            post_to_youtube(file_path, caption, caption)
        elif platform == 'X Post':
            post_to_twitter(file_path, caption)
        else:
            logging.warning(f"Unknown platform: {platform}")
    except Exception as e:
        logging.error(f"Error posting to {platform}: {str(e)}")
        raise