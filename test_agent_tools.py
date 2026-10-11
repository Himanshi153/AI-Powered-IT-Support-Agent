from state import AgentState
from reasoning import reasoning_node
from agent_tools import run_tool_from_decision


state: AgentState = {
    "messages": [],
    "issue": "My laptop is running very slowly",
    "tool_results": [],
    "step_count": 0,
    "approval_status": "not_required",
}

# Step 1: LLM decides which tool to use
state = reasoning_node(state)

print("\nREASONING DECISION:")
print(state["messages"][-1]["content"])

# Step 2: Execute the selected tool through JSON-RPC
state = run_tool_from_decision(state)

print("\nTOOL RESULT:")
print(state["tool_results"][-1])

print("\nSTEP COUNT:")
print(state["step_count"])