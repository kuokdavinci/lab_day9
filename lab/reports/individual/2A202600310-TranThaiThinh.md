# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Thái Thịnh - 2A202600310
**Vai trò trong nhóm:** MCP Owner & Trace & Docs Owner (Sprint 3 & 4)  
**Ngày nộp:** 14/04/2026  

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Xây dựng External Tools (Sprint 3) và Đánh giá luồng Trace (Sprint 4).

**Module/file tôi chịu trách nhiệm:**
- Tập tin cốt lõi: `lab/mcp_server.py` (Mock Model Context Server) và `lab/eval_trace.py` (đánh giá).
- Các files Report / Docs: `routing_decisions.md` và `single_vs_multi_comparison.md`.
- Functions tôi implement trực tiếp: `dispatch_tool()`, `tool_brave_search()` và tích hợp vào luồng đo lường Performance/Confidence của Graph.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** 
Xây dựng MCP Server dưới dạng In-process Mock Dispatcher (`dispatch_tool()`) trực tiếp trong Python thay vì làm một HTTP/FastAPI server rời rạc.

**Lý do:**
Với kiến trúc micro-agent trong bài lab, mỗi lần chuyển qua Graph đã tốn thời gian chờ đợi LLM. Việc tạo tiếp 1 HTTP Server chuẩn MCP tốn thêm network request overhead. 

**Trade-off đã chấp nhận:**
Đánh đổi ở đây là tính chuẩn xác của giao thức MCP . 

**Bằng chứng từ trace/code:**
Việc Dispatch nhanh xuất hiện trong trace `115223.json` khi Agent chỉ tốn vỏn vẹn không tới 0.05 giây để lấy ticket Jira.  
```python
# Đoạn code in-process trong mcp_server.py tôi tạo:
def dispatch_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name not in TOOL_REGISTRY: return {"error": f"Tool '{tool_name}' không tồn tại."}
    try:
        return TOOL_REGISTRY[tool_name](**tool_input)
    except TypeError as e:
        return {"error": f"Invalid input: {e}"}
```

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** LLM Output parser bị crash và trả về Exception khi LLM cấp thiếu tham số lúc gọi MCP Tools.


**Cách sửa:**
bọc toàn bộ khối thực thi trong hàm `dispatch_tool` bằng `try/except TypeError:` và đính kèm nguyên lý do thiếu biến để nhả về lại output dạng Text thông thường. Từ đó, Agent sẽ "đọc" được dòng báo lỗi và tự retry thay vì sập luồng Python.

**Bằng chứng trước/sau:**
```json
// SAU KHI SỬA (Lỗi được bắt và gói gém dưới dạng output an toàn cho LLM tự sửa):
"mcp_tools_used": [
  {
    "tool": "get_ticket_info",
    "input": {},
    "output": null,
    "error": {
      "code": "MCP_CALL_FAILED",
      "reason": "Invalid input for tool 'get_ticket_info': missing 1 required positional argument: 'ticket_id'"
    }
  }
]
```

---

## 4. Tôi tự đánh giá đóng góp của mình (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**
Tổ chức lại toàn bộ hệ thống file logging trace ra JSON logic rành mạch. 

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Tính năng Web Search (dựa vào `tool_brave_search`) vẫn gây tắc nghẽn luồng quá nặng, vì có những case tôi cho gọi API lấy mạng tốn tới >20s mới có response, làm ảnh hưởng Avg Latency chung.

**Phần tôi phụ thuộc vào thành viên khác:**
moi người phụ trách Graph chặn đứng các for loop . Nếu không chặn số lượng max_step, MCP của sẽ chịu bị spam req cho đến lúc hết token

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ tách Synchronous khi gọi Jina Web Search / Jina Embeddings thành các API Asynchronous và gọi theo luồng Streaming.  Nếu có Stream, UI sẽ mượt mà hơn và không block terminal.

---
