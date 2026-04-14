import sys
import os
# Thêm thư mục lab vào path để import graph
sys.path.append(os.path.abspath("lab"))

from graph import supervisor_node
from dotenv import load_dotenv

load_dotenv("lab/.env")

test_queries = [
    {
        "task": "SLA của ticket P1 quy định như thế nào?",
        "expected": "retrieval_worker"
    },
    {
        "task": "Khách hàng mua Flash Sale muốn hoàn tiền có được không?",
        "expected": "policy_tool_worker"
    },
    {
        "task": "Cách cấp quyền truy cập Level 3?",
        "expected": "policy_tool_worker"
    },
    {
        "task": "Quy trình nghỉ phép của công ty.",
        "expected": "retrieval_worker"
    }
]

print("="*60)
print(f"{'QUERY':<40} | {'ROUTE':<20} | {'RESULT'}")
print("-"*60)

for case in test_queries:
    state = {
        "task": case["task"],
        "history": [],
        "workers_called": []
    }
    result = supervisor_node(state)
    route = result.get("supervisor_route")
    
    status = "✅ PASS" if route == case["expected"] else "❌ FAIL"
    print(f"{case['task'][:38]:<40} | {str(route):<20} | {status}")

print("="*60)
