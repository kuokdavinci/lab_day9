# Project Plan: Multi-Agent Orchestration Lab (Day 09)

This document outlines the tasks required to refactor the RAG pipeline into a Supervisor-Worker architecture as specified in `lab/README.md`.

## Sprint 1: Refactor Graph (Foundation)
**Goal:** Transition from a "monolith" pipeline to a graph-based orchestration.

- [ ] **Implement Routing Logic in `graph.py`**
    - [ ] Update `supervisor_node()` to analyze the task and decide the route.
    - [ ] Add keyword-based routing:
        - `refund`, `policy` → `policy_tool_worker`
        - `access`, `emergency` → `policy_tool_worker`
        - `P1`, `escalation`, `ticket` → `retrieval_worker`
        - Default → `retrieval_worker`
    - [ ] Ensure `route_reason` and `risk_high` (for P1/emergency) are correctly set in the state.
- [ ] **Verify Graph Connectivity**
    - [ ] Ensure the transitions `supervisor → route → [worker] → synthesis → END` are working.
    - [ ] Test with at least 2 different query types to confirm routing.

## Sprint 2: Build Workers (Core Logic)
**Goal:** Implement the actual retrieval, policy checking, and synthesis logic.

- [ ] **Implement Retrieval Worker (`workers/retrieval.py`)**
    - [ ] Connect to the `day09_docs` ChromaDB collection.
    - [ ] Implement dense retrieval using `SentenceTransformer`.
    - [ ] Return top-k chunks and populate `retrieved_chunks` in the state.
- [ ] **Implement Policy Tool Worker (`workers/policy_tool.py`)**
    - [ ] Implement logic to check policies (e.g., refund rules, SLA).
    - [ ] Handle special cases: Flash Sale items, digital products, and P1 ticket escalation rules.
    - [ ] Initial version can be rule-based, then upgrade to LLM-based analysis.
- [ ] **Implement Synthesis Worker (`workers/synthesis.py`)**
    - [ ] Implement LLM call using grounded prompt (answer based *only* on context).
    - [ ] Ensure output includes citations (e.g., `[1]`) and a confidence score.
    - [ ] Populate `final_answer` and `confidence` in the state.
- [ ] **Integration**
    - [ ] Uncomment the worker calls in `graph.py` and replace placeholders with actual worker functions.
    - [ ] Update `contracts/worker_contracts.yaml` to mark workers as "done".

## Sprint 3: Add MCP (External Capabilities)
**Goal:** Abstract tool calls using the Model Context Protocol.

- [ ] **Implement Mock MCP Server (`mcp_server.py`)**
    - [ ] Implement `search_kb(query, top_k)` tool (wrapping ChromaDB).
    - [ ] Implement `get_ticket_info(ticket_id)` tool (mock database).
- [ ] **Refactor Policy Worker to use MCP**
    - [ ] Change `workers/policy_tool.py` to call the MCP client instead of direct DB access.
    - [ ] Ensure tool calls and results are recorded in the trace state.
- [ ] **(Bonus)** Implement a real HTTP MCP server for extra credit.

## Sprint 4: Trace, Evaluation & Documentation
**Goal:** Measure performance and document the architecture.

- [ ] **Execution & Tracing**
    - [ ] Run the pipeline against all 15 questions in `data/test_questions.json`.
    - [ ] Save all execution traces to `artifacts/traces/`.
- [ ] **Evaluation (`eval_trace.py`)**
    - [ ] Implement `analyze_trace()` to calculate average confidence, latency, and success rates.
    - [ ] Implement `compare_single_vs_multi()` by importing Day 08 baseline results.
- [ ] **Documentation**
    - [ ] Fill `docs/system_architecture.md` with the graph design.
    - [ ] Fill `docs/routing_decisions.md` with examples of supervisor routing.
    - [ ] Fill `docs/single_vs_multi_comparison.md` with the comparative analysis.
- [ ] **Reporting**
    - [ ] Complete the group report in `reports/group_report.md`.
    - [ ] Ensure every team member has an individual report in `reports/individual/`.

---

## Technical Stack
- **Framework:** Custom Graph (or LangGraph)
- **Database:** ChromaDB (Day 08 Index)
- **Embeddings:** `all-MiniLM-L6-v2`
- **LLM:** OpenAI (GPT-4o/4o-mini) or Gemini 1.5 Pro/Flash
- **Protocol:** MCP (Model Context Protocol)
