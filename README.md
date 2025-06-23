# RAG Pipeline Repository

This repository demonstrates a complete Retrieval-Augmented Generation (RAG) pipeline that:

1. **Ingests** unstructured data from Google Drive via webhooks  
2. **Indexes** document chunks into ChromaDB (HTTP service)  
3. **Answers** user queries over the indexed content with an LLM  

---

## 🚀 Components

| Component                        | Port  | Description                                                                          |
|----------------------------------|-------|--------------------------------------------------------------------------------------|
| **ChromaDB HTTP Service**        | 8000  | Vector store; run with `chroma run --path ./chroma_store`                           |
| **Webhook Receiver (FastAPI)**   | 8080  | Receives Google Drive `changes.watch` notifications, downloads & re-indexes files. The re-indexes happen only for the modified sections of the file    |
| **Query API (FastAPI)**          | 4000  | Accepts user queries, retrieves context from ChromaDB, and generates answers via LLM |

---

## 📦 Prerequisites

- Python 3.9+  
- [ChromaDB CLI](https://github.com/chroma-core/chroma)  
- `pip` or `poetry` for Python dependencies  
- (Optional) [ngrok](https://ngrok.com/) for local HTTPS tunneling  

---

## Environment Setup

1. **Clone the repo**  
   ```bash
   git clone https://github.com/Yudhishthira1406/RAG_pipeline.git
   cd RAG_pipeline
   ```
2. **Create and activate a virtual environment**
  ```
  python -m venv venv
  source venv/bin/activate
  ```
3. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```
4. **Create a .env file in the folder and set the environment variables**
  ```
  # Google Drive API Configuration
  GOOGLE_KEY_PATH=key.json

  # Page Token Configuration
  START_PAGE_TOKEN_PATH=start_page_token.json

  # AI/ML Model Configuration
  EMBED_MODEL=all-MiniLM-L6-v2
  OPENAI_MODEL=gemini-2.5-flash
  OPENAI_API_KEY={openai-key}
  ```
5. **Obtain a Google API key and store it in `key.json`**
   
   a. Go to https://console.cloud.google.com/apis/credentials <br>
   b. Create a project and add a service account <br>
   c. Go to the service account and navigate to `Keys` tab.<br>
   d. Click on add key -> Select JSON format. <br>
   e. Save the downloaded file in the root folder of the repository and rename it to key.json
![image](https://github.com/user-attachments/assets/4ffc0ad8-d52d-41bb-b268-e38c733aac94)

7. **Obtain an OpenAI key from GEMINI and update it in .env file**


## Running the vectorstore

Start the ChromaDB HTTP service (creates or reuses ./chroma_store):
```
chroma run --path ./chroma_store
```
By default, the server listens on http://localhost:8000.

## Webhook Receiver (Port 8080)
1. **Obtain the ngrok URL**
   ```
   ngrok http 8080
   ```
   Update the .env file with ngrok URL
   ```
   WEBHOOK_ADDRESS={ngrok-url}/notifications
   ```

2. **Run the webhook setup to register the application with Google Drive**
   ```
   python webhook_channel_setup.py
   ```
3. **Start the webhook server**
   ```
   uvicorn apps.webhook_server.webhook_server:app \
   --port 8080 --reload
   ```

## Query API (Port 4000)
This FastAPI app implements a /ask endpoint.
1. **Start the service**
  ```
  uvicorn apps.query_service.main:app \
  --port 4000 --reload
  ```
2. **Test with `curl`**
```
curl -X POST http://localhost:4000/ask \
-H "Content-Type: application/json" \
-d '{"query":"tell me about futures and options on the au stock exchange and give details","top_k":3}'
```

## Scope of Improvement
1. Better parsing of files, e.g., differentiate between normal text, tables and graphs.
2. Use plugin architecture for different AI agents.
3. Do keyword + vector search both to fetch the context.
4. Do contextual retrieval (https://www.anthropic.com/news/contextual-retrieval)
   


