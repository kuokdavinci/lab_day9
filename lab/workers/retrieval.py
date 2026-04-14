"""
workers/retrieval.py — Retrieval Worker
Sprint 2: Implement retrieval từ ChromaDB, trả về chunks + sources.

Input (từ AgentState):
    - task: câu hỏi cần retrieve
    - (optional) retrieved_chunks nếu đã có từ trước

Output (vào AgentState):
    - retrieved_chunks: list of {"text", "source", "score", "metadata"}
    - retrieved_sources: list of source filenames
    - worker_io_log: log input/output của worker này

Gọi độc lập để test:
    python workers/retrieval.py
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load env variables for standalone test
load_dotenv()

# ─────────────────────────────────────────────
# Worker Contract (xem contracts/worker_contracts.yaml)
# Input:  {"task": str, "top_k": int = 3}
# Output: {"retrieved_chunks": list, "retrieved_sources": list, "error": dict | None}
# ─────────────────────────────────────────────

WORKER_NAME = "retrieval_worker"
DEFAULT_TOP_K = 3


def _get_embedding_fn():
    """
    Trả về embedding function sử dụng Jina AI (mặc định).
    """
    jina_key = os.getenv("JINA_API_KEY")
    if not jina_key:
        raise ValueError("JINA_API_KEY missing in environment variables.")

    model_name = os.getenv("JINA_EMBEDDING_MODEL", "jina-embeddings-v3")

    def embed(text: str) -> list:
        url = "https://api.jina.ai/v1/embeddings"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {jina_key}"
        }
        data = {
            "model": model_name,
            "task": "retrieval.query",
            "input": [text]
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]

    return embed


def rerank_chunks(query: str, chunks: list, top_n: int = 3) -> list:
    """
    Sử dụng Jina Reranker để sắp xếp lại các chunks.
    """
    jina_key = os.getenv("JINA_API_KEY")
    rerank_model = os.getenv("JINA_RERANK_MODEL", "jina-reranker-v2-base-multilingual")

    if not jina_key or not chunks:
        return chunks[:top_n]

    try:
        url = "https://api.jina.ai/v1/rerank"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {jina_key}"
        }
        documents = [c["text"] for c in chunks]
        data = {
            "model": rerank_model,
            "query": query,
            "documents": documents,
            "top_n": top_n
        }
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        
        results = response.json()["results"]
        reranked_chunks = []
        for res in results:
            idx = res["index"]
            chunk = chunks[idx].copy()
            chunk["rerank_score"] = res["relevance_score"]
            reranked_chunks.append(chunk)
            
        return reranked_chunks
    except Exception as e:
        print(f"⚠️  Jina Rerank failed: {e}")
        return chunks[:top_n]


def _get_collection():
    """
    Kết nối ChromaDB collection.
    TODO Sprint 2: Đảm bảo collection đã được build từ Step 3 trong README.
    """
    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    try:
        collection = client.get_collection("day09_docs")
    except Exception:
        # Auto-create nếu chưa có
        collection = client.get_or_create_collection(
            "day09_docs",
            metadata={"hnsw:space": "cosine"}
        )
        print(f"⚠️  Collection 'day09_docs' chưa có data. Chạy index script trong README trước.")
    return collection


def retrieve_dense(query: str, top_k: int = DEFAULT_TOP_K) -> list:
    """
    Dense retrieval: embed query → query ChromaDB → Jina Rerank → trả về top_k chunks.
    """
    try:
        embed = _get_embedding_fn()
        query_embedding = embed(query)
        
        collection = _get_collection()
        # Lấy nhiều hơn top_k để có không gian cho rerank
        initial_top_k = top_k * 3
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=initial_top_k,
            include=["documents", "distances", "metadatas"]
        )

        chunks = []
        if results["documents"] and results["documents"][0]:
            for doc, dist, meta in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0]
            ):
                chunks.append({
                    "text": doc,
                    "source": meta.get("source", "unknown"),
                    "score": round(1 - dist, 4),  # cosine similarity
                    "metadata": meta,
                })

        # Apply Reranking
        if chunks:
            chunks = rerank_chunks(query, chunks, top_n=top_k)

        return chunks

    except Exception as e:
        print(f"❌ Retrieval Error: {e}")
        return []
        print(f"⚠️  ChromaDB query failed: {e}")
        return []


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với retrieved_chunks và retrieved_sources
    """
    task = state.get("task", "")
    top_k = state.get("retrieval_top_k", DEFAULT_TOP_K)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])

    state["workers_called"].append(WORKER_NAME)

    # Log worker IO (theo contract)
    worker_io = {
        "worker": WORKER_NAME,
        "input": {"task": task, "top_k": top_k},
        "output": None,
        "error": None,
    }

    try:
        chunks = retrieve_dense(task, top_k=top_k)

        sources = list({c["source"] for c in chunks})

        state["retrieved_chunks"] = chunks
        state["retrieved_sources"] = sources

        worker_io["output"] = {
            "chunks_count": len(chunks),
            "sources": sources,
        }
        state["history"].append(
            f"[{WORKER_NAME}] retrieved {len(chunks)} chunks from {sources}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "RETRIEVAL_FAILED", "reason": str(e)}
        state["retrieved_chunks"] = []
        state["retrieved_sources"] = []
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    # Ghi worker IO vào state để trace
    state.setdefault("worker_io_logs", []).append(worker_io)

    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Retrieval Worker — Standalone Test")
    print("=" * 50)

    test_queries = [
        "SLA ticket P1 là bao lâu?",
        "Điều kiện được hoàn tiền là gì?",
        "Ai phê duyệt cấp quyền Level 3?",
    ]

    for query in test_queries:
        print(f"\n> Query: {query}")
        result = run({"task": query})
        chunks = result.get("retrieved_chunks", [])
        print(f"  Retrieved: {len(chunks)} chunks")
        for c in chunks[:2]:
            score_val = c.get("rerank_score", c.get("score", 0))
            print(f"    [{score_val:.3f}] {c['source']}: {c['text'][:80]}...")
        print(f"  Sources: {result.get('retrieved_sources', [])}")

    print("\n✅ retrieval_worker test done.")
