from state import AgentState


state: AgentState = {
    "messages": [],
    "issue": "My laptop is running very slowly",
    "tool_results": [],
    "step_count": 0,
    "approval_status": "not_required",
}

print("STATE CREATED SUCCESSFULLY")
print(state)