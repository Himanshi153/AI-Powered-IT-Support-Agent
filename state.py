from typing import TypedDict, List, Dict, Any


class AgentState(TypedDict):
    messages: List[Dict[str, Any]]
    issue: str
    tool_results: List[Dict[str, Any]]
    step_count: int
    approval_status: str