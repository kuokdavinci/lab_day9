"""
graph.py — Supervisor Orchestrator
Sprint 1: Implement AgentState, supervisor_node, route_decision và kết nối graph.

Kiến trúc:
    Input → Supervisor → [retrieval_worker | policy_tool_worker | human_review] → synthesis → Output

Chạy thử:
    python graph.py
"""

import json
import os
from datetime import datetime
from typing import TypedDict, Literal, Optional
from dotenv import load_dotenv

# Load environment variables from lab/.env if it exists, otherwise from .env
if os.path.exists("lab/.env"):
    load_dotenv("lab/.env")
else:
    load_dotenv()

# Uncomment nếu dùng LangGraph:
# from langgraph.graph import StateGraph, END

# ─────────────────────────────────────────────
# 1. Shared State — dữ liệu đi xuyên toàn graph
# ─────────────────────────────────────────────

class AgentState(TypedDict):
    # Input
    task: str                           # Câu hỏi đầu vào từ user

    # Supervisor decisions
    route_reason: str                   # Lý do route sang worker nào
    risk_high: bool                     # True → cần HITL hoặc human_review
    needs_tool: bool                    # True → cần gọi external tool qua MCP
    hitl_triggered: bool                # True → đã pause cho human review

    # Worker outputs
    retrieved_chunks: list              # Output từ retrieval_worker
    retrieved_sources: list             # Danh sách nguồn tài liệu
    policy_result: dict                 # Output từ policy_tool_worker
    mcp_tools_used: list                # Danh sách MCP tools đã gọi

    # Final output
    final_answer: str                   # Câu trả lời tổng hợp
    sources: list                       # Sources được cite
    confidence: float                   # Mức độ tin cậy (0.0 - 1.0)

    # Trace & history
    history: list                       # Lịch sử các bước đã qua
    workers_called: list                # Danh sách workers đã được gọi
    supervisor_route: str               # Worker được chọn bởi supervisor
    latency_ms: Optional[int]           # Thời gian xử lý (ms)
    run_id: str                         # ID của run này


def make_initial_state(task: str) -> AgentState:
    """Khởi tạo state cho một run mới."""
    return {
        "task": task,
        "route_reason": "",
        "risk_high": False,
        "needs_tool": False,
        "hitl_triggered": False,
        "retrieved_chunks": [],
        "retrieved_sources": [],
        "policy_result": {},
        "mcp_tools_used": [],
        "final_answer": "",
        "sources": [],
        "confidence": 0.0,
        "history": [],
        "workers_called": [],
        "supervisor_route": "",
        "latency_ms": None,
        "run_id": f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
    }


# ─────────────────────────────────────────────
# 2. Supervisor Node — quyết định route
# ─────────────────────────────────────────────

def supervisor_node(state: AgentState) -> AgentState:
    """
    Supervisor phân tích task và quyết định:
    1. Route sang worker nào
    2. Có cần MCP tool không
    3. Có risk cao cần HITL không

    TODO Sprint 1: Implement routing logic dựa vào task keywords.
    """
    task = state["task"].lower()
    state["history"].append(f"[supervisor] received task: {state['task'][:80]}")

    # --- TODO: Implement routing logic ---
    # Gợi ý:
    # - "hoàn tiền", "refund", "flash sale", "license" → policy_tool_worker
    # - "cấp quyền", "access level", "level 3", "emergency" → policy_tool_worker
    # - "P1", "escalation", "sla", "ticket" → retrieval_worker
    # - mã lỗi không rõ (ERR-XXX), không đủ context → human_review
    # - còn lại → retrieval_worker

    route = "retrieval_worker"         # Default route
    route_reason = "general inquiry"
    needs_tool = False
    risk_high = False

    # 1. Nhóm ƯU TIÊN CAO: P1, SLA, Ticket (Luôn route sang Retrieval trước)
    priority_retrieval = ["p1", "sla", "ticket", "escalation", "incident"]
    
    # 2. Nhóm từ khóa gợi ý Policy Tool (Cần ra quyết định, check ngoại lệ)
    policy_keywords = [
        "hoàn tiền", "refund", "flash sale", "license", "digital", "kỹ thuật số",
        "cấp quyền", "access", "level 3", "permission", "admin", "phê duyệt", "approver",
        "trả hàng", "return", "policy"
    ]
    
    # 3. Nhóm từ khóa gợi ý Retrieval khác
    retrieval_keywords = [
        "quy trình", "hướng dẫn", "thủ tục", "faq", "văn bản", "thành viên",
        "thông tin", "nghỉ phép", "mã lỗi", "wifi", "vpn", "mật khẩu"
    ]

    # LOGIC ROUTING CÓ ƯU TIÊN VÀ XỬ LÝ CHỒNG LẤN
    has_priority = any(kw in task for kw in priority_retrieval)
    has_policy = any(kw in task for kw in policy_keywords)

    if has_policy:
        # Nếu có từ khóa Policy/Access, ưu tiên Policy Worker vì nó thông minh hơn trong việc xử lý luật
        route = "policy_tool_worker"
        route_reason = "task contains policy/access keyword (overriding priority retrieval if present)"
        needs_tool = True
    elif has_priority:
        # Nếu chỉ có P1/SLA mà không liên quan Policy đặc thù
        route = "retrieval_worker"
        route_reason = "priority retrieval based on P1/SLA keyword"
    elif "ERR-" in task.upper():
        route = "human_review"
        route_reason = "unknown error code detected - needs expert review"
    elif any(kw in task for kw in retrieval_keywords):
        route = "retrieval_worker"
        route_reason = "standard retrieval task"
    else:
        route = "retrieval_worker"
        route_reason = "generic request (defaulting to retrieval)"

    # 3. Nhóm rủi ro cao cần flag
    risk_keywords = [
        "emergency", "khẩn cấp", "khẩn", "ngay lập tức", "critical", "urgent", "gấp",
        "trực tiếp", "sập", "ngừng hoạt động"
    ]

    if any(kw in task for kw in risk_keywords):
        risk_high = True
        route_reason += " | risk_high detected"

    state["supervisor_route"] = route
    state["route_reason"] = route_reason
    state["needs_tool"] = needs_tool
    state["risk_high"] = risk_high
    state["history"].append(f"[supervisor] route={route} reason={route_reason}")

    return state


# ─────────────────────────────────────────────
# 3. Route Decision — conditional edge
# ─────────────────────────────────────────────

def route_decision(state: AgentState) -> Literal["retrieval_worker", "policy_tool_worker", "human_review"]:
    """
    Trả về tên worker tiếp theo dựa vào supervisor_route trong state.
    Đây là conditional edge của graph.
    """
    route = state.get("supervisor_route", "retrieval_worker")
    return route  # type: ignore


# ─────────────────────────────────────────────
# 4. Human Review Node — HITL placeholder
# ─────────────────────────────────────────────

from workers.research import web_search

def human_review_node(state: AgentState) -> AgentState:
    """
    Node xử lý các case khó/lạ (Smart HITL with LIVE Research).
    Quy trình: Deep Research Internet -> Nếu có giải pháp thì gợi ý -> Hỏi Human.
    """
    task = state["task"]
    reason = state["route_reason"]
    state["hitl_triggered"] = True
    state["workers_called"].append("human_review")
    
    print(f"\n🌐 [INTERNET RESEARCH] Agent đang tra cứu thực tế trên Internet cho mã lỗi: {task}")
    search_result = web_search(task)
    
    if search_result and len(search_result) > 100:
        print("💡 [RESEARCH SUGGESTION] Đã tìm thấy thông tin từ Internet:")
        print("-" * 30)
        print(search_result[:500] + "...") # Hiển thị snippet
        print("-" * 30)
        
        confirm = input("\n👉 Bạn có muốn sử dụng kết quả tra cứu này làm căn cứ không? (y/n): ").lower()
        if confirm == 'y':
            state["history"].append("[human_review] Solved via Live Web Research")
            state["retrieved_chunks"].append({
                "text": f"Dữ liệu tra cứu Internet: {search_result[:2000]}",
                "source": "Internet_Research",
                "score": 1.0
            })
            # Sau khi có kết quả research, ta có thể nhảy tới synthesis
            state["supervisor_route"] = "synthesis_worker"
            return state

    # Nếu không tìm thấy hoặc người dùng muốn xử lý thủ công
    print("\n" + "!" * 60)
    print(f"🛑 [HUMAN-IN-THE-LOOP REQUIRED] Cần chuyên gia xử lý trực tiếp.")
    print(f"   Lý do  : {reason}")
    print(f"   Nhiệm vụ: {task}")
    print("!" * 60)
    
    confirm = input("\n👉 Bạn có hướng xử lý giải quyết case này không? (y/n): ").lower()
    
    if confirm == 'y':
        solution = input("📝 Vui lòng nhập hướng xử lý của chuyên gia: ")
        state["history"].append(f"[human_review] APPROVED with manual solution: {solution}")
        state["final_answer"] = f"Giải pháp từ chuyên gia hệ thống: {solution}"
        state["supervisor_route"] = "done"
    else:
        state["history"].append(f"[human_review] REJECTED by expert")
        state["final_answer"] = "Yêu cầu đã bị từ chối sau khi tra cứu Internet và tham vấn chuyên gia thất bại."
        state["supervisor_route"] = "done" 
    
    return state


# ─────────────────────────────────────────────
# 5. Import Workers
# ─────────────────────────────────────────────

# TODO Sprint 2: Uncomment sau khi implement workers
from workers.retrieval import run as retrieval_run
from workers.policy_tool import run as policy_tool_run
from workers.synthesis import run as synthesis_run


def retrieval_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi retrieval worker."""
    # TODO Sprint 2: Thay bằng retrieval_run(state)
    return retrieval_run(state)


def policy_tool_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi policy/tool worker."""
    # TODO Sprint 2: Thay bằng policy_tool_run(state)
    return policy_tool_run(state)


def synthesis_worker_node(state: AgentState) -> AgentState:
    """Wrapper gọi synthesis worker."""
    # TODO Sprint 2: Thay bằng synthesis_run(state)
    return synthesis_run(state)


# ─────────────────────────────────────────────
# 6. Build Graph
# ─────────────────────────────────────────────

def build_graph():
    """
    Xây dựng graph với supervisor-worker pattern.

    Option A (đơn giản — Python thuần): Dùng if/else, không cần LangGraph.
    Option B (nâng cao): Dùng LangGraph StateGraph với conditional edges.

    Lab này implement Option A theo mặc định.
    TODO Sprint 1: Có thể chuyển sang LangGraph nếu muốn.
    """
    # Option A: Simple Python orchestrator
    def run(state: AgentState) -> AgentState:
        import time
        start = time.time()

        # Step 1: Supervisor decides route
        state = supervisor_node(state)

        # Step 2: Route to appropriate worker
        route = route_decision(state)

        if route == "human_review":
            state = human_review_node(state)
        elif route == "policy_tool_worker":
            state = policy_tool_worker_node(state)
        else:
            state = retrieval_worker_node(state)

        # Step 3: Hội tụ về Synthesis nếu nhiệm vụ chưa kết thúc (Done/Rejected)
        if state.get("supervisor_route") != "done":
            state = synthesis_worker_node(state)

        state["latency_ms"] = int((time.time() - start) * 1000)
        state["history"].append(f"[graph] completed in {state['latency_ms']}ms")
        return state

    return run


# ─────────────────────────────────────────────
# 7. Public API
# ─────────────────────────────────────────────

_graph = build_graph()


def run_graph(task: str) -> AgentState:
    """
    Entry point: nhận câu hỏi, trả về AgentState với full trace.

    Args:
        task: Câu hỏi từ user

    Returns:
        AgentState với final_answer, trace, routing info, v.v.
    """
    state = make_initial_state(task)
    result = _graph(state)
    return result


def save_trace(state: AgentState, output_dir: str = "./artifacts/traces") -> str:
    """Lưu trace ra file JSON."""
    os.makedirs(output_dir, exist_ok=True)
    filename = f"{output_dir}/{state['run_id']}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    return filename


# ─────────────────────────────────────────────
# 8. Manual Test - tesst
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("Day 09 Lab — Supervisor-Worker Graph")
    print("=" * 60)

    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "ERR-403-AUTH là lỗi gì?"
    ]

    for query in test_queries:
        print(f"\n> Query: {query}")
        result = run_graph(query)
        print(f"  Route   : {result['supervisor_route']}")
        print(f"  Reason  : {result['route_reason']}")
        print(f"  Workers : {result['workers_called']}")
        print(f"  Answer  :\n{result['final_answer']}")
        print(f"  Sources : {result.get('sources', [])}")
        print(f"  Confidence: {result['confidence']}")
        if result.get("hitl_triggered"):
            print(f"  ⚠️  HITL TRIGGERED: Confidence too low or risky task. Needs human verification!")
        print(f"  Latency : {result['latency_ms']}ms")

        # Lưu trace
        trace_file = save_trace(result)
        print(f"  Trace saved → {trace_file}")

    print("\n✅ graph.py test complete. Implement TODO sections in Sprint 1 & 2.")
