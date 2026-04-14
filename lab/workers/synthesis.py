"""
workers/synthesis.py — Synthesis Worker
Sprint 2: Tổng hợp câu trả lời từ retrieved_chunks và policy_result.

Input (từ AgentState):
    - task: câu hỏi
    - retrieved_chunks: evidence từ retrieval_worker
    - policy_result: kết quả từ policy_tool_worker

Output (vào AgentState):
    - final_answer: câu trả lời cuối với citation
    - sources: danh sách nguồn tài liệu được cite
    - confidence: mức độ tin cậy (0.0 - 1.0)

Gọi độc lập để test:
    python workers/synthesis.py
"""

import os
from dotenv import load_dotenv

# Load env variables for standalone test
load_dotenv()
if os.path.exists("lab/.env"):
    load_dotenv("lab/.env")

WORKER_NAME = "synthesis_worker"

SYSTEM_PROMPT = """Bạn là chuyên gia tổng hợp thông tin (Synthesis Worker) của hệ thống IT Helpdesk & CS. 
Nhiệm vụ của bạn là phản hồi người dùng một cách chính xác, dứt khoát và chỉ dựa trên bằng chứng được cung cấp.

QUY TẮC NGHIÊM NGẶT (STRICT RULES):
1. ĐA NGUỒN (MULTI-SOURCE): Trả lời dựa trên "TÀI LIỆU THAM KHẢO". Nếu thông tin không có trong tài liệu nội bộ nhưng có trong 'Internet_Research', hãy sử dụng nó để giải đáp và ghi chú rõ nguồn tra cứu ngoài.
2. ƯU TIÊN KẾT QUẢ POLICY: Nếu phần "KẾT QUẢ PHÂN TÍCH CHÍNH SÁCH" ghi là "KHÔNG HỢP LỆ / BỊ TỪ CHỐI", câu trả lời của bạn phải tập trung giải thích lý do tại sao yêu cầu bị từ chối.
3. TRÍCH DẪN NGUỒN (UX CITATION): Liệt kê ĐẦY ĐỦ các file nguồn tại mục "Căn cứ pháp lý/tài liệu" ở cuối bài theo định dạng: [file1.txt], [Internet_Research].
4. KHÔNG HALLUCINATE: Nếu context (cả nội bộ và Internet) đều không chứa câu trả lời, hãy nói: "Tôi rất tiếc, thông tin này hiện chưa có trong cơ sở tri thức của chúng tôi."
5. ĐỊNH DẠNG PHẢN HỒI:
   - **Kết quả**: [Được chấp thuận / Bị từ chối / Thông tin hướng dẫn]
   - **Giải thích chi tiết**: (Dùng bullet points nếu cần thiết)
   - **Căn cứ pháp lý/tài liệu**: (Liệt kê tất cả nguồn trong ngoặc vuông [])
"""


def _call_llm(messages: list, response_format: dict = None) -> str:
    """Gọi OpenAI để xử lý yêu cầu."""
    try:
        from openai import OpenAI
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        params = {
            "model": "gpt-4o-mini",
            "messages": messages,
            "temperature": 0,
        }
        if response_format:
            params["response_format"] = response_format
            
        response = client.chat.completions.create(**params)
        return response.choices[0].message.content
    except Exception as e:
        return f"[ERROR] LLM Call failed: {e}"


def _llm_as_judge(task: str, context: str, answer: str) -> dict:
    """Sử dụng LLM-as-a-Judge khắt khe để chấm điểm và giải trình."""
    if "không tìm thấy thông tin" in answer.lower() or "ERROR" in answer:
        return {"score": 0.0, "reason": "Abstain: No information found."}

    prompt = f"""Bạn là một giám khảo chuyên nghiệp đánh giá chất lượng RAG.
    Hãy đánh giá câu trả lời dựa trên Context và Task.
    
    Bảng chấm điểm (Ưu tiên UX trích dẫn ở cuối):
    - Trừ 0.3 điểm: Nếu câu trả lời quá ngắn (dưới 2 câu) hoặc thiếu phần giải thích chi tiết.
    - Trừ 0.2 điểm: Nếu KHÔNG có mục "Căn cứ pháp lý/tài liệu" ở cuối bài hoặc không liệt kê file nguồn tham khảo trong ngoặc vuông [].
    - Trừ 0.5 điểm: Nếu có thông tin sai lệch so với Context (Hallucination).
    - Khuyến khích: Trích dẫn tập trung ở cuối để tăng trải nghiệm đọc cho người dùng.
    
    Task: {task}
    Context: {context}
    Câu trả lời: {answer}
    
    Hãy chấm điểm công tâm (Scale 0.0 - 1.0). 
    Trả về JSON: {{"score": float, "reason": "lý do cụ thể cho điểm số này"}}
    """
    try:
        import json
        res_raw = _call_llm([{"role": "user", "content": prompt}], response_format={"type": "json_object"})
        res = json.loads(res_raw)
        return {
            "score": float(res.get("score", 0.5)),
            "reason": res.get("reason", "No reason provided.")
        }
    except:
        return {"score": 0.5, "reason": "Judge error, defaulting."}


def _build_context(chunks: list, policy_result: dict) -> str:
    """Xây dựng context string từ chunks và policy result."""
    parts = []

    if chunks:
        parts.append("=== TÀI LIỆU THAM KHẢO ===")
        for i, chunk in enumerate(chunks, 1):
            source = chunk.get("source", "unknown")
            text = chunk.get("text", "")
            parts.append(f"Nguồn: {source}\nNội dung: {text}")

    if policy_result:
        parts.append("\n=== KẾT QUẢ PHÂN TÍCH CHÍNH SÁCH ===")
        status = "HỢP LỆ" if policy_result.get("policy_applies") else "KHÔNG HỢP LỆ / BỊ TỪ CHỐI"
        parts.append(f"Trạng thái: {status}")
        
        if policy_result.get("explanation"):
            parts.append(f"Giải thích từ chuyên gia: {policy_result['explanation']}")
            
        if policy_result.get("exceptions_found"):
            parts.append("Các vi phạm phát hiện:")
            for ex in policy_result["exceptions_found"]:
                parts.append(f"- {ex.get('rule', '')}")
        
        if policy_result.get("policy_version_note"):
            parts.append(f"Ghi chú phiên bản: {policy_result['policy_version_note']}")

    if not parts:
        return "(Không có dữ liệu đầu vào)"

    return "\n\n".join(parts)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float:
    """
    Ước tính confidence dựa vào:
    - Số lượng và quality của chunks
    - Có exceptions không
    - Answer có abstain không

    TODO Sprint 2: Có thể dùng LLM-as-Judge để tính confidence chính xác hơn.
    """
    if not chunks:
        return 0.1  # Không có evidence → low confidence

    if "Không đủ thông tin" in answer or "không có trong tài liệu" in answer.lower():
        return 0.3  # Abstain → moderate-low

    # Weighted average của chunk scores
    if chunks:
        avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
    else:
        avg_score = 0

    # Penalty nếu có exceptions (phức tạp hơn)
    exception_penalty = 0.05 * len(policy_result.get("exceptions_found", []))

    confidence = min(0.95, avg_score - exception_penalty)
    return round(max(0.1, confidence), 2)


def _estimate_confidence(chunks: list, answer: str, policy_result: dict) -> float:
    """Ước tính confidence dựa trên heuristic (không gọi LLM)."""
    if not chunks:
        return 0.1
    if "tài liệu nội bộ hiện chưa có thông tin" in answer:
        return 0.3
    
    # Trung bình cộng score của các chunks (giả định 0.8 nếu không có score)
    avg_chunk_score = sum(c.get("score", 0.8) for c in chunks) / len(chunks)
    
    # Trừ điểm nếu có vi phạm chính sách
    penalty = 0.2 if not policy_result.get("policy_applies", True) else 0.0
    
    return round(max(0.1, min(0.95, avg_chunk_score - penalty)), 2)


def synthesize(task: str, chunks: list, policy_result: dict) -> dict:
    """
    Tổng hợp câu trả lời và so sánh 2 loại điểm confidence.
    """
    context = _build_context(chunks, policy_result)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Câu hỏi: {task}\n\n{context}\n\nHãy trả lời dựa trên dữ liệu trên."}
    ]

    answer = _call_llm(messages)
    sources = list({c.get("source", "unknown") for c in chunks})
    
    # So sánh 2 phương pháp chấm điểm
    confidence_heuristic = _estimate_confidence(chunks, answer, policy_result)
    judge_info = _llm_as_judge(task, context, answer)

    # HITL Trigger based on Judge Score
    hitl_triggered = judge_info["score"] < 0.5

    return {
        "answer": answer,
        "sources": sources,
        "confidence": judge_info["score"],
        "judge_reason": judge_info["reason"],
        "hitl_triggered": hitl_triggered,
        "debug_scores": {
            "heuristic": confidence_heuristic,
            "judge": judge_info["score"]
        }
    }


def run(state: dict) -> dict:
    """
    Worker entry point — gọi từ graph.py.
    """
    task = state.get("task", "")
    chunks = state.get("retrieved_chunks", [])
    policy_result = state.get("policy_result", {})

    state.setdefault("workers_called", [])
    state.setdefault("history", [])
    state["workers_called"].append(WORKER_NAME)

    worker_io = {
        "worker": WORKER_NAME,
        "input": {
            "task": task,
            "chunks_count": len(chunks),
            "has_policy": bool(policy_result),
        },
        "output": None,
        "error": None,
    }

    try:
        result = synthesize(task, chunks, policy_result)
        state["final_answer"] = result["answer"]
        state["sources"] = result["sources"]
        state["confidence"] = result["confidence"]
        state["judge_reason"] = result["judge_reason"]
        state["hitl_triggered"] = result.get("hitl_triggered", False)
        state["debug_scores"] = result["debug_scores"]

        worker_io["output"] = {
            "answer_length": len(result["answer"]),
            "sources": result["sources"],
            "confidence": result["confidence"],
            "judge_reason": result["judge_reason"],
            "heuristic_score": result["debug_scores"]["heuristic"]
        }
        state["history"].append(
            f"[{WORKER_NAME}] Judge: {result['confidence']} ({result['judge_reason']}), Heuristic: {result['debug_scores']['heuristic']}"
        )

    except Exception as e:
        worker_io["error"] = {"code": "SYNTHESIS_FAILED", "reason": str(e)}
        state["final_answer"] = f"SYNTHESIS_ERROR: {e}"
        state["confidence"] = 0.0
        state["history"].append(f"[{WORKER_NAME}] ERROR: {e}")

    state.setdefault("worker_io_logs", []).append(worker_io)
    return state


# ─────────────────────────────────────────────
# Test độc lập
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Synthesis Worker — Standalone Test")
    print("=" * 50)

    test_state = {
        "task": "SLA ticket P1 là bao lâu?",
        "retrieved_chunks": [
            {
                "text": "Ticket P1: Phản hồi ban đầu 15 phút kể từ khi ticket được tạo. Xử lý và khắc phục 4 giờ. Escalation: tự động escalate lên Senior Engineer nếu không có phản hồi trong 10 phút.",
                "source": "sla_p1_2026.txt",
                "score": 0.92,
            }
        ],
        "policy_result": {},
    }

    result = run(test_state.copy())
    print(f"\nAnswer:\n{result['final_answer']}")
    print(f"\nSources: {result['sources']}")
    print(f"Confidence: {result['confidence']}")

    print("\n--- Test 2: Exception case ---")
    test_state2 = {
        "task": "Khách hàng Flash Sale yêu cầu hoàn tiền vì lỗi nhà sản xuất.",
        "retrieved_chunks": [
            {
                "text": "Ngoại lệ: Đơn hàng Flash Sale không được hoàn tiền theo Điều 3 chính sách v4.",
                "source": "policy_refund_v4.txt",
                "score": 0.88,
            }
        ],
        "policy_result": {
            "policy_applies": False,
            "exceptions_found": [{"type": "flash_sale_exception", "rule": "Flash Sale không được hoàn tiền."}],
        },
    }
    result2 = run(test_state2.copy())
    print(f"\nAnswer:\n{result2['final_answer']}")
    print(f"Confidence: {result2['confidence']}")

    print("\n✅ synthesis_worker test done.")
