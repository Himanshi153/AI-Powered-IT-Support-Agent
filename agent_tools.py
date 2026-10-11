import asyncio

from dotenv import load_dotenv
from langfuse import get_client

from state import AgentState
from mcp_client import call_mcp_tool
from hooks import pre_tool_hook, post_tool_hook

load_dotenv(override=True)
langfuse = get_client()


def run_tool_from_decision(state: AgentState) -> AgentState:
    """Execute an MCP tool with validation hooks and Langfuse tracing."""

    decision = state["messages"][-1]["content"]

    tool_name = decision["tool_name"]
    arguments = decision["arguments"]

    # Record the JSON-RPC request without credentials.
    rpc_request = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
        "id": 1,
    }

    with langfuse.start_as_current_observation(
        as_type="span",
        name="mcp-tool-execution",
        input=rpc_request,
    ) as span:

        try:
            # -------------------------
            # PRE-TOOL HOOK
            # -------------------------
            validation = pre_tool_hook(
                tool_name,
                arguments,
            )

            if not validation["valid"]:
                error_result = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": validation["status_code"],
                        "message": validation["error"],
                    },
                    "id": 1,
                }

                state["tool_results"].append(error_result)
                state["step_count"] += 1

                span.update(
                    output=error_result,
                    metadata={
                        "tool_name": tool_name,
                        "status": "validation_error",
                        "http_status": validation["status_code"],
                    },
                )

                return state

            # -------------------------
            # MCP TOOL CALL
            # -------------------------
            result = asyncio.run(
                call_mcp_tool(
                    tool_name,
                    arguments,
                )
            )

            tool_output = [
                item.text if hasattr(item, "text") else str(item)
                for item in result.content
            ]

            # -------------------------
            # POST-TOOL HOOK
            # -------------------------
            post_result = post_tool_hook(
                tool_name,
                arguments,
                tool_output,
            )

            rpc_response = {
                "jsonrpc": "2.0",
                "result": post_result,
                "id": 1,
            }

            state["tool_results"].append(rpc_response)
            state["step_count"] += 1

            span.update(
                output=rpc_response,
                metadata={
                    "tool_name": tool_name,
                    "status": "success",
                    "step_count": state["step_count"],
                },
            )

            return state

        except Exception as exc:
            error_result = {
                "jsonrpc": "2.0",
                "error": {
                    "code": 500,
                    "message": str(exc),
                },
                "id": 1,
            }

            state["tool_results"].append(error_result)
            state["step_count"] += 1

            span.update(
                output={
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1000],
                },
                metadata={
                    "tool_name": tool_name,
                    "status": "execution_error",
                    "http_status": 500,
                },
            )

            return state