from typing import Literal

from langgraph.graph import StateGraph, END

from state import AgentState
from reasoning import reasoning_node
from agent_tools import run_tool_from_decision


MAX_STEPS = 10
MAX_RECOVERY_ATTEMPTS = 2


def route_after_reasoning(
    state: AgentState,
) -> Literal["tool", "finish"]:
    """Route the workflow based on the agent's latest decision."""

    if state["step_count"] >= MAX_STEPS:
        return "finish"

    messages = state.get("messages", [])

    if not messages:
        return "finish"

    decision = messages[-1].get("content", {})

    if not isinstance(decision, dict):
        return "finish"

    if decision.get("action") == "tool":
        return "tool"

    return "finish"


def route_after_tool(
    state: AgentState,
) -> Literal["reasoning", "finish"]:
    """Return to reasoning after a tool result, within safe limits."""

    if state["step_count"] >= MAX_STEPS:
        return "finish"

    tool_results = state.get("tool_results", [])

    if not tool_results:
        return "finish"

    last_result = tool_results[-1]

    # Detect JSON-RPC errors and tool execution failures.
    has_error = (
        isinstance(last_result, dict)
        and (
            "error" in last_result
            or last_result.get("isError") is True
        )
    )

    if has_error:
        # Allow limited recovery attempts before stopping.
        error_count = sum(
            1
            for result in tool_results
            if isinstance(result, dict)
            and (
                "error" in result
                or result.get("isError") is True
            )
        )

        if error_count > MAX_RECOVERY_ATTEMPTS:
            return "finish"

    # Give the reasoning node the result so it can decide
    # whether to recover or produce the final response.
    return "reasoning"


def final_response(state: AgentState) -> dict:
    """Ensure the workflow returns a final assistant response."""

    messages = state.get("messages", [])

    latest_decision = None

    for message in reversed(messages):
        if message.get("role") != "assistant":
            continue

        content = message.get("content", {})

        if isinstance(content, dict):
            latest_decision = content
            break

    # Preserve an existing final response.
    if (
        latest_decision
        and latest_decision.get("action") == "final"
        and state["step_count"] < MAX_STEPS
    ):
        return state

    # If the step limit has been reached, return a safe message.
    if state["step_count"] >= MAX_STEPS:
        state["messages"].append(
            {
                "role": "assistant",
                "content": {
                    "action": "final",
                    "tool_name": "",
                    "arguments": {},
                    "response": (
                        "I could not complete troubleshooting within "
                        "the allowed step limit. Please try again."
                    ),
                },
            }
        )

    # If the graph stopped without a final answer, provide a fallback.
    elif not (
        latest_decision
        and latest_decision.get("action") == "final"
    ):
        state["messages"].append(
            {
                "role": "assistant",
                "content": {
                    "action": "final",
                    "tool_name": "",
                    "arguments": {},
                    "response": (
                        "I could not determine a final answer. "
                        "Please try again with more details."
                    ),
                },
            }
        )

    return state


def build_agent_graph():
    """Build the IT Support Agent reasoning and tool workflow."""

    workflow = StateGraph(AgentState)

    workflow.add_node("reasoning", reasoning_node)
    workflow.add_node("tool_execution", run_tool_from_decision)
    workflow.add_node("final_response", final_response)

    workflow.set_entry_point("reasoning")

    workflow.add_conditional_edges(
        "reasoning",
        route_after_reasoning,
        {
            "tool": "tool_execution",
            "finish": "final_response",
        },
    )

    workflow.add_conditional_edges(
        "tool_execution",
        route_after_tool,
        {
            "reasoning": "reasoning",
            "finish": "final_response",
        },
    )

    workflow.add_edge("final_response", END)

    return workflow.compile()


agent_graph = build_agent_graph()