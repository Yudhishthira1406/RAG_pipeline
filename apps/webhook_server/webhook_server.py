import os
from apps.webhook_server.drive_api import download_and_index_files
from fastapi import FastAPI, Request, Response
import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from apps.utils.token_store import load_start_page_token, save_start_page_token


SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_KEY_PATH")
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

app = FastAPI()

@app.post("/notifications")
async def receive_notification(request: Request):
    headers = request.headers
    if headers.get("X-Goog-Channel-Token") != "my_secret_channel_token":
        return Response(status_code=403)

    page_token = load_start_page_token()
    if not page_token:
        return Response(status_code=500, content="Missing pageToken")
    changes = drive_service.changes().list(pageToken=page_token).execute()
    print(changes)
    for change in changes.get("changes", []):
        file_id = change.get("fileId")
        if not file_id or change.get("removed", False):
            continue
        download_and_index_files(change.get("fileId"), change.get("file").get("name"))

    # Update page token
    if "newStartPageToken" in changes:
        save_start_page_token(changes["newStartPageToken"])

    return Response(status_code=200)