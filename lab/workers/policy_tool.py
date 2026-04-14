"""
workers/policy_tool.py — Policy & Tool Worker
Sprint 2+3: Kiểm tra policy dựa vào context, gọi MCP tools khi cần.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: context từ retrieval_worker
    - needs_tool: True nếu supervisor quyết định cần tool call

Output (vào AgentState):
    - policy_result: {"policy_applies", "policy_name", "exceptions_found", "source", "rule"}
    - mcp_tools_used: list of tool calls đã thực hiện
    - worker_io_log: log

Gọi độc lập để test:
    python workers/policy_tool.py
"""

import os
import sys
from typing import Optional
from dotenv import load_dotenv

# Load env variables for standalone test
load_dotenv()
if os.path.exists("lab/.env"):
    load_dotenv("lab/.env")

WORKER_NAME = "policy_tool_worker"


# ─────────────────────────────────────────────
# MCP Client — Sprint 3: Thay bằng real MCP call
# ─────────────────────────────────────────────

def _call_mcp_tool(tool_name: str, tool_input: dict) -> dict:
    """
    Gọi MCP tool.

    Sprint 3 TODO: Implement bằng cách import mcp_server hoặc gọi HTTP.

    Hiện tại: Import trực tiếp từ mcp_server.py (trong-process mock).
    """
    from datetime import datetime

    try:
        # TODO Sprint 3: Thay bằng real MCP client nếu dùng HTTP server
        from mcp_server import dispatch_tool
        result = dispatch_tool(tool_name, tool_input)
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": result,
            "error": None,
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        return {
            "tool": tool_name,
            "input": tool_input,
            "output": None,
            "error": {"code": "MCP_CALL_FAILED", "reason": str(e)},
            "timestamp": datetime.now().isoformat(),
        }


# ─────────────────────────────────────────────
# Policy Analysis Logic
# ─────────────────────────────────────────────

def analyze_policy(task: str, chunks: list) -> dict:
    """
    Phân tích policy dựa trên context chunks kết hợp Rule-based và LLM.
    """
    task_lower = task.lower()
    context_text = "\n\n".join([f"Source: {c.get('source')}\nContent: {c.get('text')}" for c in chunks])
    
    # --- Layer 1: Rule-based fast check ---
    exceptions_found = []
    policy_name = "refund_policy_v4"
    
    # Rule 1-3: Flash Sale, Digital, Activation (Strict Policy v4)
    if "flash sale" in task_lower or "flash sale" in context_text.lower():
        exceptions_found.append({"type": "flash_sale_exception", "rule": "Đơn hàng Flash Sale không được hoàn tiền (Điều 3).", "source": "policy_refund_v4.txt"})

    if any(kw in task_lower for kw in ["license", "key", "subscription", "kỹ thuật số"]):
        exceptions_found.append({"type": "digital_product_exception", "rule": "Sản phẩm nội dung số không được hoàn tiền (Điều 3).", "source": "policy_refund_v4.txt"})

    if any(kw in task_lower for kw in ["đã kích hoạt", "đã dùng", "activated", "đã đăng ký"]):
        exceptions_found.append({"type": "activated_exception", "rule": "Sản phẩm đã kích hoạt hoặc sử dụng không đủ điều kiện hoàn tiền (Điều 3).", "source": "policy_refund_v4.txt"})

    # Rule 4: Temporal Scoping
    policy_version_note = ""
    if any(kw in task_lower for kw in ["trước 01/02", "31/01", "30/01"]):
        policy_version_note = "Đơn hàng đặt trước 01/02/2026 áp dụng chính sách v3."

    # --- Layer 2: LLM analysis fallback ---
    openai_key = os.getenv("OPENAI_API_KEY")
    # Khởi tạo từ kết quả Layer 1
    policy_applies = len(exceptions_found) == 0
    explanation = "Yêu cầu tuân thủ các quy tắc cơ bản." if policy_applies else "Yêu cầu bị từ chối dựa trên các quy tắc cứng."

    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            
            prompt = f"""Bạn là chuyên gia thẩm định chính sách. Dựa trên Context, hãy xác định yêu cầu hoàn tiền của khách hàng có hợp lệ không (True/False).
            
            Task: {task}
            Context: {context_text}
            
            Trả về JSON:
            {{
                "policy_applies": boolean,
                "extra_exceptions": ["lý do"],
                "explanation": "giải thích chi tiết"
            }}
            """
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                response_format={"type": "json_object"}
            )
            import json
            analysis = json.loads(response.choices[0].message.content)
            
            if analysis.get("policy_applies") is False:
                policy_applies = False
            
            explanation = analysis.get("explanation", explanation)
            for ex in analysis.get("extra_exceptions", []):
                exceptions_found.append({"type": "llm_detected_exception", "rule": ex, "source": "LLM Analysis"})

        except Exception as e:
            print(f" LLM Analysis failed: {e}")

    # Final decision
    policy_applies = (len(exceptions_found) == 0) and policy_applies
    sources = list({c.get("source", "unknown") for c in chunks if c})

    return {
        "policy_applies": bool(policy_applies),
        "policy_name": policy_name,
        "exceptions_found": exceptions_found,
        "source": sources,
        "policy_version_note": policy_version_note,
        "explanation": explanation,
    }


# ─────────────────────────────────────────────
# Worker Entry Point
# ─────────────────────────────────────────────

def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.

    Args:
        state: AgentState dict

    Returns:
        Updated AgentState với policy_result và mcp_tools_used
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    needs_tool = state.get("needs_tool", False)

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state.setdefault("mcp_tools_used", [])

    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "needs_tool": needs_tool,
        },
        "output": None,
        "error": None,
    }

    try:
        # Step 1: Nếu chưa có chunks, gọi MCP search_kb
        if not chunks and needs_tool:
            mcp_result = _call_mcp_tool("search_kb", {"query": task, "top_k": 3})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP search_kb")

            if mcp_result.get("output") and mcp_result["output"].get("chunks"):
                chunks = mcp_result["output"]["chunks"]
                state["retrieved_chunks"] = chunks

        # Step 2: Phân tích policy
        policy_result = analyze_policy(task, chunks)
        state["policy_result"] = policy_result

        # Step 3: Nếu cần thêm info từ MCP (e.g., ticket status), gọi get_ticket_info
        if needs_tool and any(kw in task.lower() for kw in ["ticket", "p1", "jira"]):
            mcp_result = _call_mcp_tool("get_ticket_info", {"ticket_id": "P1-LATEST"})
            state["mcp_tools_used"].append(mcp_result)
            state["history"].append(f"[{WORKER_NAME}] called MCP get_ticket_info")

        worker_io["output"] = {
            "policy_applies": policy_result["policy_applies"],
            "exceptions_count": len(policy_result.get("exceptions_found", [])),
            "mcp_calls": len(state["mcp_tools_used"]),
        }
        state["history"].append(
            f"[{WORKER_NAME}] policy_applies={policy_result['policy_applies']}, "
            f"exceptions={len(policy_result.get('exceptions_found', []))}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "POLICY_CHECK_FAILED", "reason": str(e)}
        state["policy_result"] = {"error": str(e)}
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Policy Tool Worker — Standalone Test")
    print("=" * 50)

    test_cases = [
        {
            "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì sản phẩm lỗi — được không?",
            "retrieved_chunks": [
                {"text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.9}
            ],
        },
        {
            "task": "Khách hàng muốn hoàn tiền license key đã kích hoạt.",
            "retrieved_chunks": [
                {"text": "Sản phẩm kỹ thuật số (license key, subscription) không được hoàn tiền.", "source": "policy_refund_v4.txt", "score": 0.88}
            ],
        },
        {
            "task": "Khách hàng yêu cầu hoàn tiền trong 5 ngày, sản phẩm lỗi, chưa kích hoạt.",
            "retrieved_chunks": [
                {"text": "Yêu cầu trong 7 ngày làm việc, sản phẩm lỗi nhà sản xuất, chưa dùng.", "source": "policy_refund_v4.txt", "score": 0.85}
            ],
        },
    ]

    for tc in test_cases:
        print(f"\n> Task: {tc['task'][:70]}...")
        result = run(tc.copy())
        pr = result.get("policy_result", {})
        print(f"  policy_applies: {pr.get('policy_applies')}")
        if pr.get("exceptions_found"):
            for ex in pr["exceptions_found"]:
                print(f"  exception: {ex['type']} — {ex['rule'][:60]}...")
        print(f"  MCP calls: {len(result.get('mcp_tools_used', []))}")

    print("\n✅ policy_tool_worker test done.")
