from typing import Literal

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from state import AgentState


def approval_node(state: AgentState):
    """
    Pause the graph and request human approval
    before a simulated high-impact action.
    """

    approval = interrupt(
        {
            "type": "human_approval",
            "message": "Approval required before applying the recommended troubleshooting change.",
            "action": "Apply the recommended troubleshooting change",
            "options": ["Approve", "Reject"],
        }
    )

    if str(approval).lower() == "approve":
        state["approval_status"] = "approved"
    else:
        state["approval_status"] = "rejected"

    state["step_count"] += 1

    return state


def approval_route(state: AgentState) -> Literal["approved", "rejected"]:
    """
    Route the workflow based on human approval.
    """

    if state["approval_status"] == "approved":
        return "approved"

    return "rejected"


def approved_node(state: AgentState):
    """
    Continue after human approval.
    """

    state["messages"].append(
        {
            "role": "system",
            "content": "Human approved the high-impact action.",
        }
    )

    state["step_count"] += 1

    return state


def rejected_node(state: AgentState):
    """
    Stop the high-impact action after human rejection.
    """

    state["messages"].append(
        {
            "role": "system",
            "content": "Human rejected the high-impact action.",
        }
    )

    state["step_count"] += 1

    return state


def build_approval_graph():
    """
    Build a LangGraph HITL workflow with checkpoint persistence.
    """

    graph = StateGraph(AgentState)

    graph.add_node("approval", approval_node)
    graph.add_node("approved", approved_node)
    graph.add_node("rejected", rejected_node)

    graph.set_entry_point("approval")

    graph.add_conditional_edges(
        "approval",
        approval_route,
        {
            "approved": "approved",
            "rejected": "rejected",
        },
    )

    graph.add_edge("approved", END)
    graph.add_edge("rejected", END)

    checkpointer = MemorySaver()

    return graph.compile(checkpointer=checkpointer)