
---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | ~0.70 | 0.82 | +0.12 | Hệ thống tự tin hơn nhờ dùng Judge đánh giá chéo. |
| Avg latency (ms) | ~3,500 | 11,457 | +7,957 | Multi-agent chạy tuần tự nhiều worker và lookup external tool. |
| Abstain rate (%) | 15% | ~6% | -9% | Khả năng tự tin hơn khi bí (Web Search) thay vì ngô nghê chối. |
| Multi-hop accuracy | Dưới 70% | 100% (15/15 success)| N/A | Pass toàn bộ test plan Day 09. |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Trace file log cực kì chi tiết minh bạch. |
| Debug time (estimate) | 20 phút | 5 phút | -15 phút| Cô lập vấn đề theo từng Agent rất nhanh. |

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Tương đối tốt | Rất tốt (100%) |
| Latency | Rất nhanh (<4s) | Khá nhanh (~6s-8s) |
| Observation | Đôi khi gom nhầm policy nếu prompt ngắn | Rất chuẩn xác nhờ Retrieval Worker cô lập. |

**Kết luận:** Multi-agent không làm tăng độ chính xác lên quá cao cho các câu gõ-ăn-liền rủi ro thấp, nhưng nó đảm bảo chuẩn hóa form đầu ra. Tuy nhiên Latency bị tăng do Supervisor tốn một nhịp.

---

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | Thấp, hay nhầm context | Tốt |
| Routing visible? | ✗ | ✓ |
| Observation | LLM trả lời tùy tiện giữa Rule A và DB C | Tách hẳn logic ra Policy_Tool_Worker với MCP. |

**Kết luận:**
Multi-Agent thiết kế chốt chặn rõ ràng giúp kết nối những câu hoãn, yêu cầu check ngoại lệ (như check ticket Jira + policy refund cùng lúc) siêu nhạy bén. Day 08 gần như mù tịt nếu gặp case này.

---

### 2.3 Câu hỏi cần abstain (thiếu/không có thông tin)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | LLM hay hallucinate | Tìm web ngooài |
| Hallucination cases | Nhiều | Ít |


**Kết luận:**
Nhờ Worker Synthesis, các câu hỏi ambiguous sẽ bị gạt bỏ bằng mức confidence = 0.0 để đẩy cờ HITL (nhờ người can thiệp).

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: 20-30 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc file trace json → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing heuristics.
  → Nếu retrieval sai → test retrieval_worker.py độc lập.
  → Nếu synthesis sai → test sysnthesis.py với fixed input.
Thời gian ước tính: 3-5 phút
```

**Câu cụ thể nhóm đã debug:** _(Mô tả 1 lần debug thực tế trong lab)_
Ở Task `Cần cấp quyền Level 3 để khắc phục P1...`, Supervisor route đúng vào Policy, nhưng final answer lại đi nói chuyện "Hoàn tiền". Khi xem trace, nhìn được ngay list exceptions là "hoàn tiền không áp dụng". Chỉ cần vào nhánh `policy_tool_worker.py` sửa lại cái Rule kiểm tra Keyword hoàn tiền/cấp quyền. Cô lập bug hoàn hảo.

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa khối Chain/Prompt gốc | Khai báo trong thư viện MCP `mcp_server.py`. |
| Thêm 1 domain mới | Retrain prompt lớn | Thêm 1 worker mới (VD: HR_Worker). |
| Thay đổi retrieval strategy | Sửa module lõi | Chỉ Sửa `retrieval.py` độc lập. |
| A/B test một phần | Khó — Phải duplicate file | Dễ — Switch cờ Supervisor đụng trúng Worker V2. |

**Nhận xét:**
Kiến trúc Micro-service hóa quy trình prompt giúp hệ thống Agent mọc dài ra như con bạch tuộc mà không sợ phình to cái não Supervisor.

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query | 1 LLM call | 1-2 LLM calls (LLM judge) |
| Complex query | 1 LLM call (dễ tạch) | 2-3 LLM calls (Judge, Policy) |
| MCP tool call | N/A | Tùy tool (có web search) |


---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. Khả năng **Cách ly rủi ro / Quản lý Bug**: Pipeline hỏng đoạn nào biết ngay đoạn đó do JSON trace lưu IO của từng sub-worker riêng rẽ.
2. Khả năng **Xử lý linh hoạt**: Có thể bypass context, gọi các API hệ thống đặc thù thông qua MCP mà không làm nhiễu loạn những tác vụ trả lời căn bản thông thường (Retrieval).

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. Tiêu hao Latency (gấp đôi gấp ba thời gian xoay trục) và API token cost tăng vọt từ các LLM "Judge".

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi triển khai các hệ thống Q&A "trò chuyện phím" nhỏ nhặt, FAQ đơn giản tĩnh, hoặc dự án không cho phép chi tiêu API vượt mức.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Làm Router bằng LLM nhẹ thay vì if/else cứng (Zero-shot Router), và phát triển MCP client real để các Agent "nhắn tin" được trên Slack/Jira.
