import io
import json
import pymupdf 
import os
import hashlib
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from langchain.text_splitter import RecursiveCharacterTextSplitter

from dotenv import load_dotenv

load_dotenv()

# === CONFIGURATION ===
FOLDER_ID = "1MI6iLantDU4n4ZGwzuf-DBgT2ZUDLBnJ"
DOWNLOAD_DIR = 'downloads'
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

CHROMA_DIR = 'chroma_store'
COLLECTION_NAME = 'pdf_chunks'
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_KEY_PATH")  # path to your JSON key

# === GOOGLE DRIVE SETUP ===
SCOPES = ['https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
drive_service = build('drive', 'v3', credentials=creds)

# === CHROMA SETUP ===
client = chromadb.HttpClient(
    host="localhost",
    port=8000
)


# Setup embedding model manually
embedding_model = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

collection = client.get_or_create_collection(COLLECTION_NAME, embedding_function=embedding_model)


text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

MAPPING_FILE="chunk_hash_map.json"

def load_map():
    if os.path.exists(MAPPING_FILE):
        return json.load(open(MAPPING_FILE))
    return {}

def save_map(m):
    json.dump(m, open(MAPPING_FILE, "w"), indent=2)

def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

# === HELPERS ===
def list_pdfs_recursively(folder_id):
    """Recursively list all PDF files inside the folder and subfolders."""
    query = f"'{folder_id}' in parents and trashed = false"
    results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    files = results.get('files', [])
    
    all_pdfs = []
    for file in files:
        if file['mimeType'] == 'application/pdf':
            all_pdfs.append(file)
        elif file['mimeType'] == 'application/vnd.google-apps.folder':
            all_pdfs.extend(list_pdfs_recursively(file['id']))
    return all_pdfs

def download_pdf(file_id, file_name):
    request = drive_service.files().get_media(fileId=file_id)
    file_path = os.path.join(DOWNLOAD_DIR, file_name)
    fh = io.FileIO(file_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    return file_path

def extract_text_from_pdf(path):
    doc = pymupdf.open(path)
    return "\n".join([page.get_text() for page in doc])


def download_and_index_files(file_id, file_name):
    local_path = download_pdf(file_id, file_name)

    chunk_map = load_map().get(file_id, [])
    old_hashes = {entry["chunk_id"]: entry["hash"] for entry in chunk_map}
    # Extract and split
    full_text = extract_text_from_pdf(local_path)
    chunks = text_splitter.split_text(full_text)

    new_map = []
    to_add   = []
    to_del   = []
    
    # 3. Compute hash per chunk and diff
    for i, chunk in enumerate(chunks):
        chunk_id = f"{file_id}_chunk{i}"
        h        = sha256(chunk)
        new_map.append({"chunk_id": chunk_id, "hash": h})

        if chunk_id not in old_hashes:
            # brand new chunk
            to_add.append((chunk_id, chunk))
        elif old_hashes[chunk_id] != h:
            # modified chunk
            to_del.append(chunk_id)
            to_add.append((chunk_id, chunk))
        # else: unchanged → do nothing

    # 4. Any old chunk_ids no longer in new_map should be deleted
    new_ids = {e["chunk_id"] for e in new_map}
    for old_id in old_hashes:
        if old_id not in new_ids:
            to_del.append(old_id)

    # 5. Delete outdated chunks from ChromaDB
    if to_del:
        collection.delete(ids=to_del)

    # 6. Add new/updated chunks
    if to_add:
        texts     = [c for _, c in to_add]
        ids       = [i for i, _ in to_add]
        metadatas = [{"file_id": file_id, "file_name": file_name}]*len(to_add)
        collection.add(documents=texts,metadatas=metadatas, ids=ids)

    full_map = load_map()
    full_map[file_id] = new_map
    save_map(full_map)

    print(f"Reindexed {file_name}: +{len(to_add)} chunks, -{len(to_del)} chunks")

# === MAIN INGESTION ===
def ingest_pdfs_from_drive():
    print(f"Fetching PDFs from folder: {FOLDER_ID}")
    pdf_files = list_pdfs_recursively(FOLDER_ID)
    print(f"Found {len(pdf_files)} PDF(s)")

    for file in pdf_files:
        print(f"Processing: {file['name']}")
        download_and_index_files(file["id"], file["name"])

    print("✅ Ingestion complete and saved to ChromaDB.")

    results = collection.get(include=["documents", "metadatas"])

    for i in range(len(results["documents"])):
        print(f"📄 ID: {results['ids'][i]}")
        print(f"📝 Text: {results['documents'][i][:100]}...")
        print(f"📎 Metadata: {results['metadatas'][i]}")
        print("-" * 50)

# === RUN ===
if __name__ == "__main__":
    ingest_pdfs_from_drive()
