import chromadb
import os
import requests
from dotenv import load_dotenv

# Load env variables
load_dotenv("./lab/.env")

# Setup path
chroma_path = os.path.join(os.getcwd(), 'chroma_db')
docs_dir = os.path.join(os.getcwd(), 'lab', 'data', 'docs')

jina_key = os.getenv("JINA_API_KEY")
jina_model = os.getenv("JINA_EMBEDDING_MODEL", "jina-embeddings-v3")

print(f"Indexing docs from {docs_dir} into {chroma_path} using Jina ({jina_model})...")

client = chromadb.PersistentClient(path=chroma_path)
# Delete existing collection to avoid dimension mismatch
try:
    client.delete_collection('day09_docs')
except:
    pass
col = client.get_or_create_collection('day09_docs', metadata={"hnsw:space": "cosine"})

def jina_embed_batch(texts: list) -> list:
    url = "https://api.jina.ai/v1/embeddings"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {jina_key}"
    }
    data = {
        "model": jina_model,
        "task": "retrieval.passage",
        "input": texts
    }
    response = requests.post(url, headers=headers, json=data)
    if not response.ok:
        print(f"FAILED: {response.text}")
    response.raise_for_status()
    return [d["embedding"] for d in response.json()["data"]]

docs = []
metadatas = []
ids = []

for fname in os.listdir(docs_dir):
    fpath = os.path.join(docs_dir, fname)
    if os.path.isfile(fpath):
        with open(fpath, 'r', encoding='utf-8') as f:
            content = f.read()
        docs.append(content)
        metadatas.append({'source': fname})
        ids.append(fname)
        print(f'Queueing: {fname}')

if docs:
    embeddings = jina_embed_batch(docs)
    col.add(
        documents=docs,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

print('Index ready with Jina embeddings.')
