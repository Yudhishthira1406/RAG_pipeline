
import os
import io
import pymupdf 
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from langchain.text_splitter import RecursiveCharacterTextSplitter

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

        # Extract and split
    full_text = extract_text_from_pdf(local_path)
    chunks = text_splitter.split_text(full_text)

    metadatas = [{"file_name": file_name, "file_id": file_id}] * len(chunks)
    ids = [f"{file_id}_chunk{i}" for i in range(len(chunks))]

    collection.add(
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )

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
