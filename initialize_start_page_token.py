import os
from googleapiclient.discovery import build
from google.oauth2 import service_account
from token_store import save_start_page_token, load_start_page_token

# Google Drive setup
creds = service_account.Credentials.from_service_account_file(
    os.getenv("GOOGLE_KEY_PATH"),
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive = build("drive", "v3", credentials=creds)

# Initialize token if needed
if not load_start_page_token():
    start_token = drive.changes().getStartPageToken().execute()["startPageToken"]
    save_start_page_token(start_token)
