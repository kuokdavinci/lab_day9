## 1. Tổng quan kiến trúc

> Mô tả ngắn hệ thống của nhóm: chọn pattern gì, gồm những thành phần nào.

**Pattern đã chọn:** Supervisor-Worker (với Routing Heuristic & Tool Abstraction qua MCP).
  
**Lý do chọn pattern này (thay vì single agent):**
Kiến trúc này cho phép thay đổi luồng Single RAG thành một hệ thống linh hoạt.

---

## 2. Sơ đồ Pipeline

**Sơ đồ thực tế của nhóm:**

```mermaid
flowchart TD
    A([User Task / Inquiry]) --> B(Supervisor Node)
    
    B --> |"if risk/error -> HitL"| C(Human Review Node)
    B --> |"if policy/access"| D(Policy Tool Worker)
    B --> |"else/standard"| E(Retrieval Worker)

    C <--> |Web Search API / Terminal| U((Human Expert / Web))
    D <--> |Tool Calls| M((MCP Server))
    E <--> |Dense Embeddings / Jina Rerank| DB[(ChromaDB)]

    C --> F(Synthesis Worker)
    D --> F(Synthesis Worker)
    E --> F(Synthesis Worker)

    F <--> |LLM-as-a-Judge| LLM((OpenAI GPT_4o))
    F --> G([Final Answer | Citations | Confidence])
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Cửa ngõ (entry-point) diễn dịch từ khoá task và chỉ định nhánh Worker cho câu query |
| **Input** | Raw Task string (`AgentState["task"]`) |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool` |
| **Routing logic** | Heuristics (Keyword list cứng) phân nhóm ưu tiên: 1. Chính sách/Lệnh hệ thống; 2. P1/Khẩn/SLA; 3. Lạ/Lỗi. |
| **HITL condition** | Khớp tag lạ ("ERR-"), hoặc sau cuối LLM cho điểm Judge < 0.5 thì ném warning. |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Bóc tách text -> Vector embeddings, search Semantic từ DB, trả về văn bản ngữ cảnh. |
| **Embedding model** | Default: API Jina-embeddings-v3 / all-MiniLM-L6-v2 |
| **Top-k** | k mặc định = 3, lấy dư -> Rerank qua Jina Reranker -> ra Top K sát nhất |
| **Stateless?** | Yes |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Giải quyết case phức tạo. Validate xem request có thoả mãn rule gộp (Refund/Access rule), liên thông Tool MCP. |
| **MCP tools gọi** | `search_kb`, `get_ticket_info`, v.v... |
| **Exception cases xử lý** | Đơn thẻ điện tử không hoàn, hàng ngâm quá lâu không hoàn, Level truy cập khẩn cấp. |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | OpenAI `gpt-4o-mini` |
| **Temperature** | `0` (Strictly Grounded, zero hallucination) |
| **Grounding strategy** | Strict Context only, ép format cuối có khối "Citation" trích dẫn nguồn rành rọt. |
| **Abstain condition** | Tự chấm điểm qua prompt "LLM-as-a-Judge". |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| search_kb | query, top_k | chunks, sources |
| get_ticket_info | ticket_id | ticket details (từ Mock Jira DB) |
| check_access_permission | access_level, requester_role | can_grant, approvers |
| create_ticket | priority, title, desc | mock URL, ticket ID |
| brave_search | search query | Real-time Web content |

---

## 4. Shared State Schema

> Khối State lưu vết xuyên suốt đồ thị tác vụ.

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------|
| task | str | Câu hỏi đầu vào | Cả cụm đọc |
| supervisor_route | str | Worker được chọn | supervisor ghi |
| route_reason | str | Lý do route (tag lý luận) | supervisor ghi |
| retrieved_chunks | list | Evidence từ DB / Reranker | retrieval ghi, synthesis đọc |
| policy_result | dict | Kết quả kiểm tra policy | policy_tool ghi, synthesis đọc |
| mcp_tools_used | list | Tool calls đã gọi và trả kết quả | policy_tool ghi |
| final_answer | str | Câu trả lời cuối | synthesis ghi |
| confidence | float | Mức tin cậy (qua Judge/Heuristic) | synthesis ghi |
| history | list | Array Trace Logs chạy từng Node | Tất cả các Node |
| judge_reason | str | Lời giải thích phê duyệt của trọng tài | synthesis ghi |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Khó | Dễ hơn — test từng worker IO độc lập (JSON) |
| Thêm capability mới | Phải sửa toàn prompt | Thêm worker/MCP tool riêng |
| Routing visibility | Không có | Có đầy đủ history trace,
| External Interaction | Khó | Có MCP |


---

## 6. Giới hạn và điểm cần cải tiến

1. **Routing Heuristic hard-code**: Khảo sát hiện dùng list các keyword tĩnh trong Python để Rẽ (if x in y). Nếu user ghi sai lỗi chính tả sẽ sai. 
2. **Bottel-neck lúc gọi External Tools**: Web Search / Reranker Jina quá trình request lên cloud tốn nhiều time hoặc timeout. Cần có cơ chế streaming để cải thiện UX người dùng hoặc cài cache redis.
