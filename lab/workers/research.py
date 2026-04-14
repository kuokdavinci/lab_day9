"""
workers/research.py — Research Worker (External Knowledge)
Nhiệm vụ: Tra cứu Internet để bổ sung kiến thức nằm ngoài dữ liệu nội bộ.
"""
import os
import requests

def web_search(query: str) -> str:
    """
    Sử dụng Jina Search API để tra cứu thông tin trên Internet.
    Trả về nội dung web dạng markdown.
    """
    try:
        import urllib.parse
        import time
        jina_key = os.getenv("JINA_API_KEY")
        encoded_query = urllib.parse.quote(query)
        url = f"https://s.jina.ai/{encoded_query}"
        
        headers = {
            "Accept": "text/event-stream",
            "X-With-Generated-Alt": "true" 
        }
        if jina_key:
            headers["Authorization"] = f"Bearer {jina_key}"

        print(f"   📡 Calling Jina AI Search (timeout: 30s)...")
        start_time = time.time()
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Giải mã tiếng Việt chuẩn (utf-8-sig để xử lý BOM nếu có)
        content = response.content.decode('utf-8-sig')
        
        elapsed = time.time() - start_time
        print(f"   ✅ Search complete in {elapsed:.1f}s")
        
        return content[:5000] 
    except Exception as e:
        print(f"⚠️  Web Search failed: {e}")
        return ""
