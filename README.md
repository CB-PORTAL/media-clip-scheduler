# Media Clip Scheduler

## Overview

The Media Clip Scheduler is a powerful automation tool designed to streamline your content creation and distribution process. It automatically detects new video files in a specified folder, uploads them to Google Drive, and schedules them for posting on various social media platforms using Google Calendar. This tool is ideal for content creators, social media managers, and digital marketers who want to automate and optimize the workflow of sharing their video content across multiple platforms.

## Features

- **Automatic Video Detection**: Monitors a specified folder for new video files and triggers the automation process immediately upon detection.

- **Google Drive Integration**: Securely uploads detected video files to Google Drive, ensuring easy access and management.

- **Google Calendar Scheduling**: Automatically schedules posts using a pre-configured Google Calendar, ensuring consistent content posting.

- **Multi-Platform Support**: Schedules posts across various social media platforms like YouTube Shorts, X (formerly Twitter), Facebook Stories, and Instagram Reels.

- **Customizable Posting Times**: Allows you to define a time window during which posts should be scheduled.

## Installation

### Prerequisites

- **Python 3.x**: Ensure that Python 3.x is installed on your machine.

- **Google Cloud Console Account**: You need a Google Cloud Console account to create API credentials for accessing Google Drive and Google Calendar.

### Setup Instructions

1. **Clone the Repository:**
   Clone the repository to your local machine using the following command:
   ```bash
   git clone https://github.com/your-username/media-clip-scheduler.git
   cd media-clip-scheduler

2. **Create a Virtual Environment and Install Dependencies:** 
    python -m venv venv
    On Linux/Mac use source venv/bin/activate
    On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt

3. **Set up the .env File:**
# Set up the .env File

1. Copy the provided .env.template file to create your .env file:
   ```
   cp config/.env.template .env
   ```
   
2. Open the .env file in a text editor and configure the following variables:

   - MONITOR_FOLDER: The absolute path of the folder you want to monitor for new video files.
     (e.g., E:\[Media])

   - GOOGLE_SHEET_NAME: The name of your Google Sheet where video data will be recorded.

   - CALENDAR_ID: Your Google Calendar ID where posts will be scheduled.

   - CREDENTIALS_FILE: The relative or absolute path to your Google API service account credentials JSON file.

   - POSTING_HOURS_START: The start of the time window (in 24-hour format) during which posts should be scheduled
     (e.g., 0 for midnight).

   - POSTING_HOURS_END: The end of the time window (in 24-hour format) during which posts should be scheduled
     (e.g., 24 for midnight).

   - PLATFORMS: A comma-separated list of platforms where the content will be posted
     (e.g., YouTube Shorts,X Post,Facebook Story,Instagram Reel).

4. **Obtain Google API Credentials:**
    - Create a project in the Google Cloud Console.
    - Enable the Google Drive API and Google Calendar API for your project.
    - Create a service account and download the credentials JSON file.
    - Move the credentials JSON file to the root directory of your project and update the CREDENTIALS_FILE variable in the .env file with its path.

5. **Run the Script**
    To start the Media Clip Scheduler, run the following command:
        python src/media_clip_automation.py

## Usage

- **Monitoring and Automation**: Once the script is running, it continuously monitors the specified folder for new video files.

- **File Upload**: Detected video files are automatically uploaded to Google Drive.

- **Scheduling**: The script schedules these files for posting on the specified platforms at random times within the defined time window.

- **Logging**: All activities, including errors and successful operations, are logged in media_clip_automation.log.

## Directory Structure

media-clip-scheduler/
│
├── config/
│   └── .env.template
│
├── src/
│   └── media_clip_automation.py  # Main script for initializing the automation
│
├── README.md  # The README file you are currently reading
├── .gitignore  # Specifies files and directories to be ignored by Git
├── .gitattributes
│
└── venv/  # Virtual environment directory (excluded from Git)

## .gitignore Configuration

Ensure that sensitive files and unnecessary files are not tracked by Git. Your .gitignore should include:
    .env
    service_account_credentials.json
    venv/
    logs/

## Contributions

We welcome contributions! Please feel free to submit issues or pull requests to enhance the functionality or address any bugs.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Future Enhancements

- **Social Media API Integration**: In the future, we plan to integrate directly with social media APIs to automatically post the scheduled content.

- **Advanced Scheduling**: Provide more advanced scheduling options, such as setting specific posting times for each platform.