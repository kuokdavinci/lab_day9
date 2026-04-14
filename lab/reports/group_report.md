# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Nhóm 2 người
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Lê Trung Anh Quốc | Supervisor & Trace Owner, Worker, MCP Owner | leanhquoc128@gmail.com  |
| Trần Thái Thịnh | MCP Owner, Documentation Owner, Trace Owner |  |

**Ngày nộp:** 2026-04-14
**Repo:** kuokdavinci/lab_day9
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

> Mô tả ngắn gọn hệ thống nhóm: bao nhiêu workers, routing logic hoạt động thế nào,
> MCP tools nào được tích hợp. Dùng kết quả từ `docs/system_architecture.md`.

**Hệ thống tổng quan:**
Nhóm đã xây dựng hệ thống Multi-Agent theo mô hình **Supervisor-Worker** rẽ nhánh (Branched Architecture). Hệ thống bao gồm 4 đối tượng chính được cô lập hoàn toàn về mặt logic:
1. **Retrieval Worker**: Chuyên trách tìm kiếm văn bản nội bộ từ ChromaDB.
2. **Policy Agent**: Một Agent tự trị sử dụng MCP Tools để kiểm soát các quy định (Refund, Access Control).
3. **Research Worker (Smart HITL)**: Chuyên trách tra cứu thực tế trên Internet thông qua Jina/Brave Search API để xử lý các mã lỗi lạ, edge cases.
4. **Synthesis Worker**: Tổng hợp câu trả lời cuối cùng kèm Citation và tự chấm điểm bằng LLM-as-a-Judge.

**Routing logic cốt lõi:**
Supervisor sử dụng chiến lược **Tiered Keyword Dispatching**:
- Ưu tiên 1 (Critical): Từ khóa "P1", "SLA" -> `retrieval_worker`.
- Ưu tiên 2 (Logic): Từ khóa "Policy", "Access" -> `policy_tool_worker`.
- Ưu tiên 3 (Risk): Từ khóa "ERR-", "Mã lỗi" -> `human_review` (HITL).
- Mặc định: `retrieval_worker`.

**MCP tools đã tích hợp:** 
Hệ thống tích hợp 3 tools qua MCP Server:
- `search_kb`: Semantic search nội bộ.
- `get_ticket_info`: Tra cứu trạng thái Ticket Jira.
- `brave_search`: **Tra cứu Internet thời gian thực** (Real-world capability).
---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Tách biệt hoàn toàn luồng Internet Research ra khỏi Retrieval nội bộ và tích hợp vào nút Human Review.

**Bối cảnh vấn đề:**
Ở Day 08, Agent thường bị không có kiến thức về các mã lỗi lạ, edge cases khi cố gắng tìm kiếm trong cơ sở dữ liệu nội bộ cho mọi câu hỏi. Nhóm cần một cơ chế để bảo vệ tính toàn vẹn của dữ liệu nội bộ. Đồng thời cải thiện khả năng trả lời các câu hỏi về mã lỗi, những tình huống khẩn cấp.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Gộp Search vào Retrieval | Tiện lợi, chỉ cần 1 node. | Dữ liệu rác từ internet làm nhiễu kết quả RAG nội bộ. |
| **Tách nhánh Research (Chọn)** | Cô lập dữ liệu tuyệt đối. Chỉ dùng Internet cho các Case "không thể giải quyết nội bộ". | Tăng độ phức tạp của Graph. |

**Phương án đã chọn và lý do:**
Nhóm chọn phương án tách nhánh vì tính **Safety**. Bằng cách chỉ kích hoạt `web_search` khi Supervisor phát hiện mã lỗi lạ (ERR-xxx), chúng ta đảm bảo rằng các câu hỏi về quy định (SLA, Refund) luôn sử dụng 100% dữ liệu chuẩn của công ty, không bị "hallucinate" bởi thông tin trên mạng.

**Bằng chứng từ trace/code:**
Trong trace `run_20260414_143628.json` cho câu hỏi về mã lỗi lạ:
```json
"supervisor_route": "human_review",
"route_reason": "unknown error code detected - needs expert review",
"hitl_triggered": true
```
Agent đã thực hiện `web_search` và lấy được thông tin về lỗi 403 trước khi hỏi con người để xác nhận.

---

## 3. Kết quả grading questions (150–200 từ)

> Sau khi chạy pipeline với grading_questions.json (public lúc 17:00):
> - Nhóm đạt bao nhiêu điểm raw?
> - Câu nào pipeline xử lý tốt nhất?
> - Câu nào pipeline fail hoặc gặp khó khăn?

**Tổng điểm raw ước tính:** ___ / 96

**Câu pipeline xử lý tốt nhất:**
- ID: ___ — Lý do tốt: ___________________

**Câu pipeline fail hoặc partial:**
- ID: ___ — Fail ở đâu: ___________________  
  Root cause: ___________________

**Câu gq07 (abstain):** Nhóm xử lý thế nào?

_________________

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?

_________________

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

**Metric thay đổi rõ nhất (có số liệu):**
- **Avg Confidence**: Tăng từ ~0.68 (Day 08) lên **0.82** (Day 09). Do các Worker chuyên biệt có Prompt tập trung hơn.
- **Abstain Rate**: Day 09 an toàn hơn hẳn vì hệ thống chọn "Hỏi người" thay vì trả lời bừa khi gặp keyword lạ.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**
Khả năng gỡ lỗi (Debuggability). Với Trace của Day 09, nhóm có thể biết chính xác Agent sai ở bước Routing (do Supervisor) hay sai ở bước lấy dữ liệu (do Worker), điều mà ở Day 08 là một "hộp đen" rất khó đoán.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Thời gian phản hồi (Latency) tăng đáng kể (từ ~5s lên ~14s) do phải gọi LLM nhiều lần cho Supervisor, Worker và Synthesis. Đây là sự đánh đổi cần thiết cho tính chính xác. Trường hợp cụ thể là query, các câu hỏi đơn giản, rủi ro thấp, nơi mà single-pass retrieval đã đủ hiệu quả.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

> Đánh giá trung thực về quá trình làm việc nhóm.

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
|Lê Trung Anh Quốc  | Thực hiện Supervisor Routing logic, Xây dựng Workers Logic,Thêm MCP Web Search cho Human Review Route, Xây dựng LLM as Judge dùng để đo confidence cho reply. Kiểm tra eval và report, tinh chỉnh nếu có | 1 + 2 + 4 |
|Trần Thái Thịnh | Tích hợp MCP Server (search_kb, get_ticket_info), xử lý dữ liệu Tool-call trong Policy Worker. Phát triển eval_trace.py để tự động benchmark 15 câu hỏi. Phân tích Trace JSON, đồng bộ Contract và hoàn thiện tài liệu Architecture/Comparison/Routing. | 3 + 4 |

**Điều nhóm làm tốt:**

Xây dựng được hệ thống hoàn chỉnh với các chức năng được yêu cầu trong bài lab. Hoạt động đúng với luồng được đề ra. Trace log rõ ràng, dễ dàng kiểm soát chất lượng của hệ thống

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**

Chưa tổ chức version control hiệu quả, cần lên kế hoạch kỹ càng hơn về topic mỗi người thực hiện

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**

Có thể tái tổ chức lại luồng hoặc áp dụng thêm pattern mới kiểm thử trade-offs và performance của các pattern khác nhau.
---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ triển khai một **FastAPI Server** để đóng gói toàn bộ Graph này thành một Web Service thực thụ, thay vì chạy qua CLI. Ngoài ra, sẽ tối ưu hóa việc gọi song song (Parallel) các worker để giảm Latency.
Làm Router bằng LLM nhẹ thay vì if/else cứng (Zero-shot Router), và phát triển MCP client real để các Agent "nhắn tin" được trên Slack/Jira.
Nếu được, sẽ scale hệ thống chạy concurency để handle được nhiều request cùng lúc, giảm latency xuống mức chấp nhận được.
---
*File này lưu tại: `reports/group_report.md`*  
*Commit sau 18:00 được phép theo SCORING.md*
