# Project Plan — Lab Day 09: Multi-Agent RAG Orchestration

## 🎯 Global Objective
Refactor the Day 08 "monolith" RAG into a production-grade **Supervisor-Worker** architecture with MCP tool integration, smart Human-in-the-loop (HITL), and comprehensive trace observability.

---

## 📅 Roadmap & Progress

### ✅ Sprint 1: Graph Core & Orchestration (Completed)
- [x] Define `AgentState` with history and routing metadata.
- [x] Implement `supervisor_node` with keyword-based and priority routing.
- [x] Implement Branched Execution flow (Retrieval | Policy | Human Review).
- [x] Ensure all routes converge at `synthesis_worker`.

### ✅ Sprint 2: Specialized Workers (Completed)
- [x] **Retrieval Worker**: Local ChromaDB + Jina Rerank (Isolated from internet).
- [x] **Policy Agent**: Autonomous tool-user for SOP compliance (Flash Sale, Digital Products).
- [x] **Synthesis Worker**: Grounded generation with citation grouping and LLM-as-a-Judge scoring.

### ✅ Sprint 3: MCP & Advanced HITL (Completed)
- [x] **Internal MCP**: `search_kb`, `get_ticket_info`, `check_access` mock tools.
- [x] **External MCP**: Real **Brave Search** integration via Jina Search API.
- [x] **Smart HITL**: Interactive terminal approval with automated internet research fallback.

### 🔄 Sprint 4: Evaluation & Finalization (85%)
- [x] **Benchmark Run**: Executed 15/15 questions with detailed trace logging.
- [x] **Trace Analysis**: Cumulative and per-session metrics (Routing, Confidence, Latency).
- [ ] **Final Documentation**: Update architecture, routing, and comparison docs.
- [ ] **Reporting**: Finalize group and individual lab reports.

---

## 🛠️ Technical Insights (Optimizations Made)
- **Data Isolation**: Clearly separated internal retrieval from external web research to prevent data pollution.
- **Priority Routing**: Overlapping tasks (e.g., P1 + Access) are routed to the most capable worker (Policy).
- **UX Excellence**: Citations are grouped at the end ("Căn cứ pháp lý") for better readability.
- **Resilience**: Added UTF-8-sig encoding and 30s timeouts for robust internet research.

---

## 🚀 Next Steps
1.  **Draft Documentation**: Fill templates in `lab/docs/`.
2.  **Group Report**: Summarize the multi-agent vs single-agent performance gains (Avg Confidence increased to >0.8).
3.  **Submit**: Cleanup artifacts and finalize the repository for grading.
