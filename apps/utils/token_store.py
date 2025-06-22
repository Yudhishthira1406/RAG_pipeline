import os
import json

TOKEN_FILE = os.getenv("START_PAGE_TOKEN_PATH")

def save_start_page_token(token: str):
    with open(TOKEN_FILE, "w") as f:
        json.dump({"startPageToken": token}, f)
    print(f"✅ Saved startPageToken: {token}")

def load_start_page_token() -> str | None:
    if not os.path.exists(TOKEN_FILE):
        print("⚠️ Token file not found. Call getStartPageToken() once.")
        return None
    with open(TOKEN_FILE, "r") as f:
        data = json.load(f)
        return data.get("startPageToken")
