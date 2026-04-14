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
```json
{
  "task": "ERR-403-AUTH là lỗi gì và cách xử lý?",
  "route_reason": "unknown error code detected - needs expert review",
  "risk_high": false,
  "needs_tool": false,
  "hitl_triggered": false,
  "retrieved_chunks": [
    {
      "text": "Dữ liệu tra cứu Internet: event: data\ndata: [{\"title\":\"Lỗi HTTP Error 403 Forbidden là gì? Nguyên nhân, cách sửa lỗi đơn ...\",\"url\":\"https://www.thegioididong.com/hoi-dap/loi-http-error-403-forbidden-la-gi-nguyen-nhan-cach-sua-1370605\",\"description\":\"Lỗi HTTP Error 403 Forbidden là một lỗi mã trạng thái, nghĩa rằng trang web bị chặn truy cập vì một lý do nào đó. Lỗi này xảy ra khi truy cập trang web trên cả ...\",\"content\":\"\",\"usage\":{\"tokens\":1112}},{\"title\":\"Lỗi 403 Forbidden: Nguyên nhân & cách fix chi tiết cho WordPress\",\"url\":\"https://www.bkns.vn/loi-403-forbidden-error.html\",\"description\":\"Lỗi 403 Forbidden error thường xảy ra khi bạn cố gắng truy cập vào một tài nguyên mà máy chủ không cho phép hiển thị công khai. Một trong những ...\",\"date\":\"Feb 10, 2026\",\"content\":\"\",\"usage\":{\"tokens\":1112}},{\"title\":\"Lỗi 403 Forbidden: Nó là gì? Làm thế nào để khắc phục nó?\",\"url\":\"https://www.nstbrowser.io/vi/blog/403-forbidden-error\",\"description\":\"Error 403 – Forbidden: Lỗi truy cập tổng quát. ; 403 – Forbidden: Truy cập bị từ chối bởi máy chủ, có thể là vấn đề về quyền hoặc cấu hình không ...\",\"date\":\"Jul 11, 2024\",\"content\":\"\",\"usage\":{\"tokens\":1112}},{\"title\":\"Lỗi 403 forbidden là gì? Hướng dẫn cách sửa lỗi 403 khi lướt web\",\"url\":\"https://gearvn.com/blogs/thu-thuat-giai-dap/loi-403-forbidden-la-gi?srsltid=AfmBOopJWEVVqLm2cVL7c22hqWuw7qZJkIUOjnVw-Ee8Z1gb30fi0A5P\",\"description\":\"Lỗi Error 403 Forbidden xảy ra khi bạn đang cố gắng truy cập vào một trang web mà không được phép truy cập hoặc có thể trang web đó đang bị cấm.\",\"date\":\"Sep 26, 2022\",\"content\":\"\",\"usage\":{\"tokens\":1112}},{\"title\":\"Lỗi 403 forbidden error là gì? Cách sửa lỗi nhanh và hiệu quả\",\"url\":\"https://monamedia.co/loi-403-forbidden-error-la-gi-cach-sua-loi/\",\"description\":\"“403 forbidden error” xuất hiện khi bạn truy cập vào những website bị chặn vì nhiều nguyên nhân như link website không kết nối với bất kỳ cơ sở dữ liệu nào, địa ...\",\"content\":\"\",\"usage\":{\"tokens\":1112}},{\"title\":\"Lỗi 403 là gì? Nguyên nhân và cách sửa lỗi hiệ",
      "source": "Internet_Research",
      "score": 1.0
    }
  ],
  "retrieved_sources": [],
  "policy_result": {},
  "mcp_tools_used": [],
  "final_answer": "**Kết quả**: Thông tin hướng dẫn\n\n**Giải thích chi tiết**:\n- Lỗi ERR-403-AUTH thường liên quan đến mã trạng thái HTTP 403 Forbidden, có nghĩa là truy cập vào tài nguyên bị từ chối bởi máy chủ.\n- Nguyên nhân có thể bao gồm:\n  - Quyền truy cập không đủ: Người dùng không có quyền để xem trang hoặc tài nguyên cụ thể.\n  - Cấu hình máy chủ: Có thể có vấn đề trong cấu hình máy chủ khiến cho tài nguyên không được phép truy cập.\n  - Địa chỉ IP bị chặn: Địa chỉ IP của người dùng có thể bị chặn bởi máy chủ.\n- Cách xử lý lỗi này có thể bao gồm:\n  - Kiểm tra lại quyền truy cập: Đảm bảo rằng bạn có quyền truy cập vào tài nguyên.\n  - Xóa cache và cookies: Đôi khi, việc xóa cache và cookies của trình duyệt có thể giúp khắc phục lỗi.\n  - Liên hệ với quản trị viên: Nếu bạn tin rằng bạn nên có quyền truy cập, hãy liên hệ với quản trị viên của trang web để được hỗ trợ.\n\n**Căn cứ pháp lý/tài liệu**: [Internet_Research]",
  "sources": [
    "Internet_Research"
  ],
  "confidence": 0.8,
  "history": [
    "[supervisor] received task: ERR-403-AUTH là lỗi gì và cách xử lý?",
    "[supervisor] route=human_review reason=unknown error code detected - needs expert review",
    "[human_review] Solved via Live Web Research",
    "[synthesis_worker] Judge: 0.8 (Câu trả lời cung cấp thông tin chi tiết về lỗi ERR-403-AUTH và cách xử lý, nhưng thiếu phần trích dẫn cụ thể từ các tài liệu tham khảo trong ngoặc vuông. Mặc dù có mục 'Căn cứ pháp lý/tài liệu', nhưng không liệt kê các nguồn cụ thể cho từng thông tin được nêu.), Heuristic: 0.95",
    "[graph] completed in 47311ms with 1 hops"
  ],
  "workers_called": [
    "human_review",
    "synthesis_worker"
  ],
  "supervisor_route": "synthesis_worker",
  "latency_ms": 47311,
  "run_id": "run_20260414_164237",
  "initial_route": "human_review",
  "judge_reason": "Câu trả lời cung cấp thông tin chi tiết về lỗi ERR-403-AUTH và cách xử lý, nhưng thiếu phần trích dẫn cụ thể từ các tài liệu tham khảo trong ngoặc vuông. Mặc dù có mục 'Căn cứ pháp lý/tài liệu', nhưng không liệt kê các nguồn cụ thể cho từng thông tin được nêu.",
  "debug_scores": {
    "heuristic": 0.95,
    "judge": 0.8
  },
  "worker_io_logs": [
    {
      "worker": "synthesis_worker",
      "input": {
        "task": "ERR-403-AUTH là lỗi gì và cách xử lý?",
        "chunks_count": 1,
        "has_policy": false
      },
      "output": {
        "answer_length": 911,
        "sources": [
          "Internet_Research"
        ],
        "confidence": 0.8,
        "judge_reason": "Câu trả lời cung cấp thông tin chi tiết về lỗi ERR-403-AUTH và cách xử lý, nhưng thiếu phần trích dẫn cụ thể từ các tài liệu tham khảo trong ngoặc vuông. Mặc dù có mục 'Căn cứ pháp lý/tài liệu', nhưng không liệt kê các nguồn cụ thể cho từng thông tin được nêu.",
        "heuristic_score": 0.95
      },
      "error": null
    }
  ],
  "question_id": "q09"
}

---

## 3. Kết quả grading questions (150–200 từ)

**Tổng điểm raw ước tính:** **92 / 96**

**Câu pipeline xử lý tốt nhất:**
- **ID: gq02 (Temporal Scoping)** — Lý do: Hệ thống nhận diện chính xác sự thay đổi phiên bản chính sách theo ngày hiệu lực (trước 01/02/2026) và từ chối trả lời do thiếu dữ liệu phiên bản cũ, thay vì "chế" ra câu trả lời.
- **ID: gq10 (Exception Override)** — Lý do: Agent xử lý đúng logic ưu tiên "Flash Sale" qua mặt điều kiện lỗi sản phẩm thông thường.

**Câu pipeline fail hoặc partial:**
- **ID: gq09 (Multi-hop)** — Lý do: Trả lời đúng quy trình nhưng thiếu kênh "PagerDuty" trong danh sách thông báo và nhầm lẫn nhẹ vai trò phê duyệt (hệ thống trả về Tech Lead thay vì Line Manager).
- **ID: gq01** — Lý do: Thiếu kênh "PagerDuty" trong danh sách notification mặc dù đã trích dẫn đúng file `sla_p1_2026.txt`.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?
Nhóm sử dụng cơ chế **Strict Grounding** trong `synthesis_worker`. Khi không tìm thấy con số phạt tài chính trong tài liệu SLA, Agent đã khẳng định rõ ràng: *"Tài liệu tham khảo không cung cấp thông tin cụ thể về mức phạt này"*, bảo vệ hệ thống khỏi việc Hallucination (ảo giác).

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?

Không ghi được multi hop, nhưng theo như trace log thì nó đã đi qua mỗi policy tool 1 lần, nhưng khi đối chiếu với criteria vẫn đáp ứng được 60-70% về mặt đầy đủ.

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
 ---
 
 ## 7. Hạng mục tự đánh giá (Nhóm tự chấm)
 
 | Hạng mục | Điểm tối đa | Nhóm tự chấm | Lý do/Bằng chứng |
 |----------|-------------|--------------|------------------|
 | **1. Deliverables** | 20 | **20 / 20** | Code chạy end-to-end, mọi worker test độc lập được, Trace I/O đầy đủ. |
 | **2. Documentation** | 10 | **10 / 10** | 3 file docs tại `/docs` trình bày chuyên sâu, có sơ đồ Mermaid. |
 | **3. Grading Questions** | 30 | **26 / 30** | Đáp ứng 88/96 raw points (sai sót nhỏ ở PagerDuty gq09). |
 | **4. Bonus Points** | +10 | **+3 / +10** | MCP thật (+2), Confidence LLM-as-a-Judge (+1) |
 | **TỔNG CỘNG** | **60 (+10)** | **59 / 60** |  |
 
 ---
 *File này lưu tại: `reports/group_report.md`*  
 *Commit sau 18:00 được phép theo SCORING.md*
