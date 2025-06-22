# rag_langchain.py

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from langchain.embeddings import HuggingFaceEmbeddings

import os

import chromadb

from langchain_chroma import Chroma
from langchain_openai import ChatOpenAI
from langchain.chains import RetrievalQA

# === CONFIGURATION ===
COLLECTION_NAME   = "pdf_chunks"
EMBED_MODEL_NAME  = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")
OPENAI_MODEL      = os.getenv("OPENAI_MODEL", "gemini-2.5-flash")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise EnvironmentError("Please set OPENAI_API_KEY")

# === FASTAPI APP ===
app = FastAPI(title="LangChain RAG API")

# === SETUP Chroma HTTP CLIENT ===
client = chromadb.HttpClient(
    host="localhost",
    port=8000
)# wrap in LangChain vectorstore
embeddings = HuggingFaceEmbeddings(model_name=EMBED_MODEL_NAME)

vectorstore = Chroma(
    client=client,
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings
)

# === BUILD RETRIEVER & RAG CHAIN ===
retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

llm = ChatOpenAI(model=OPENAI_MODEL, temperature=0.0, api_key=os.getenv("OPENAI_API_KEY"), base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=retriever,
    return_source_documents=True
)

# === REQUEST/RESPONSE MODELS ===
class AskRequest(BaseModel):
    query: str
    top_k: int = 5

class Source(BaseModel):
    page_content: str
    metadata: dict

class AskResponse(BaseModel):
    answer: str
    sources: list[Source]

# === API ENDPOINT ===
@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    # adjust retriever if user wants different k
    qa_chain.retriever.search_kwargs["k"] = request.top_k

    # run the chain
    result = qa_chain({"query": request.query})
    answer = result["result"]
    docs   = result["source_documents"]

    sources = [
        Source(page_content=doc.page_content, metadata=doc.metadata)
        for doc in docs
    ]

    return AskResponse(answer=answer, sources=sources)
