from reasoning import reasoning_node


state = {
    "messages": [],
    "issue": "Calculate 25 multiplied by 4",
    "tool_results": [],
    "step_count": 0,
    "approval_status": "not_required",
}


result = reasoning_node(state)


print("\n--- REASONING NODE OUTPUT ---")
print(result["messages"][-1]["content"])
print("\nStep count:", result["step_count"])