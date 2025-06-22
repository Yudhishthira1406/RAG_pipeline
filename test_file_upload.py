import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import json

SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_KEY_PATH")
FOLDER_ID = "1U2pISK1UZs6IAyDwBHV0bch7pSnbOJP9"

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/drive"]
)
drive_service = build("drive", "v3", credentials=credentials)

file_metadata = {
    "name": "test_upload13.txt",
    "parents": [FOLDER_ID]
}
media = {
    "mimeType": "text/plain",
    "body": "This is a test file content"
}

from googleapiclient.http import MediaInMemoryUpload
media_upload = MediaInMemoryUpload(media["body"].encode(), mimetype=media["mimeType"])

file = drive_service.files().create(
    body=file_metadata,
    media_body=media_upload,
    fields="id"
).execute()

print(f"Uploaded file ID: {file['id']}")
