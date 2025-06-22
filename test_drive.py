import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_KEY_PATH")
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive = build('drive', 'v3', credentials=creds)

print(drive.files().get(fileId="1MI6iLantDU4n4ZGwzuf-DBgT2ZUDLBnJ", fields="driveId, name").execute())
