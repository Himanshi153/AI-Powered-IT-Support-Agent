import asyncio
import json
import logging
import os

from dotenv import load_dotenv

load_dotenv()

from langchain_groq import ChatGroq

from state import AgentState
from mcp_client import discover_mcp_tools
from langfuse import get_client

logger = logging.getLogger(__name__)

langfuse = get_client()

# Use the existing cloud LLM configuration.
llm = ChatGroq(
    model="openai/gpt-oss-20b",
    temperature=0,
)

# Structured output schema
from pydantic import BaseModel, Field
from typing import Literal, Any


class AgentDecision(BaseModel):
    action: Literal["tool", "final"] = Field(
        description="Whether to call an MCP tool or return a final answer."
    )
    tool_name: str = Field(
        default="",
        description="Name of the MCP tool to call, or empty for final."
    )
    arguments: dict[str, Any] = Field(
        default_factory=dict,
        description="Arguments required by the selected MCP tool."
    )
    response: str = Field(
        default="",
        description="Helpful final response to the user."
    )


structured_llm = llm.with_structured_output(
    AgentDecision,
    include_raw=True,
)


def reasoning_node(state: AgentState):
    """
    Analyze the IT issue, select a tool when needed,
    recover from tool errors, and finish after success.
    """

    with langfuse.start_as_current_observation(
        as_type="span",
        name="it-support-reasoning",
        input={
            "issue": state["issue"],
            "step_count": state["step_count"],
            "previous_tool_results": state["tool_results"][-3:],
        },
    ) as span:

        try:
            issue = state["issue"]
            previous_error = ""
            successful_result = None

            # -------------------------------------------------
            # 1. Inspect the previous tool execution
            # -------------------------------------------------
            if state.get("tool_results"):
                last_result = state["tool_results"][-1]

                if isinstance(last_result, dict):

                    # Handle JSON-RPC tool errors
                    if "error" in last_result:
                        error_data = last_result["error"]

                        if isinstance(error_data, dict):
                            error_message = error_data.get(
                                "message",
                                str(error_data),
                            )
                        else:
                            error_message = str(error_data)

                        previous_error = (
                            "The previous tool request failed.\n"
                            f"Error: {error_message}\n"
                            "Correct the arguments and retry only if "
                            "the issue is recoverable."
                        )

                    # Handle successful JSON-RPC tool responses
                    result_data = last_result.get("result")

                    if isinstance(result_data, dict):
                        if result_data.get("status") == "success":
                            successful_result = result_data.get(
                                "result",
                                "",
                            )

                    # Handle MCP responses marked as errors
                    if last_result.get("isError") is True:
                        previous_error = (
                            "The previous MCP tool execution failed. "
                            "Choose a safe recovery action."
                        )

            # -------------------------------------------------
            # 2. Stop after successful tool execution
            # -------------------------------------------------
            if successful_result is not None:
                if isinstance(successful_result, list):
                    result_text = ", ".join(
                        str(item) for item in successful_result
                    )
                elif isinstance(successful_result, dict):
                    result_text = json.dumps(
                        successful_result,
                        ensure_ascii=False,
                    )
                else:
                    result_text = str(successful_result)

                decision_data = {
                    "action": "final",
                    "tool_name": "",
                    "arguments": {},
                    "response": (
                        f"The tool executed successfully. "
                        f"Result: {result_text}"
                    ),
                }

                state["messages"].append({
                    "role": "assistant",
                    "content": decision_data,
                })

                state["step_count"] += 1

                span.update(
                    output={
                        "decision": decision_data,
                        "step_count": state["step_count"],
                    },
                    metadata={
                        "status": "success",
                        "reason": "tool_execution_completed",
                    },
                )

                return state

            # -------------------------------------------------
            # 3. Discover available MCP tools
            # -------------------------------------------------
            mcp_tools = asyncio.run(discover_mcp_tools())

            if not mcp_tools:
                raise RuntimeError(
                    "No MCP tools are available from the MCP server."
                )

            tool_descriptions = "\n".join(
                [
                    (
                        f"- {tool['name']}: {tool.get('description', '')}\n"
                        f"  Input schema: {tool.get('input_schema', {})}"
                    )
                    for tool in mcp_tools
                ]
            )

            # -------------------------------------------------
            # 4. Build the reasoning prompt
            # -------------------------------------------------
            prompt = f"""
You are an AI-powered IT Support Agent.

User issue:
{issue}

Previous tool error, if any:
{previous_error or "No previous tool error."}

Available MCP tools:
{tool_descriptions}

Choose exactly one action:

A. action="tool"
Use a tool only when it is necessary to diagnose or solve the issue.
The tool_name must exactly match one of the available MCP tools.
Provide arguments matching its input schema.

B. action="final"
Return a useful answer directly if no tool is required.

Rules:
1. Never invent a tool name or argument.
2. Never execute a tool yourself.
3. Do not claim a tool succeeded unless its result confirms success.
4. If the previous tool failed, correct the problem before retrying.
5. Do not repeat an identical failed tool request.
6. If recovery is not possible, explain the limitation in a final answer.
7. If a calculator tool is available and the issue requires calculation,
   use the calculator tool.
8. When choosing action="final", provide a non-empty response.
9. Return one structured decision only.
"""

            # -------------------------------------------------
            # 5. Ask the LLM for a structured decision
            # -------------------------------------------------
            llm_result = structured_llm.invoke(prompt)

            if llm_result.get("parsing_error") is not None:
                raise ValueError(
                    "Could not parse the model decision: "
                    f"{llm_result['parsing_error']}"
                )

            decision = llm_result.get("parsed")

            if decision is None:
                raise ValueError(
                    "The LLM did not return a valid structured decision."
                )

            decision_data = decision.model_dump()

            # -------------------------------------------------
            # 6. Validate the proposed decision
            # -------------------------------------------------
            available_tool_names = {
                tool["name"] for tool in mcp_tools
            }

            if decision_data["action"] == "tool":

                tool_name = decision_data["tool_name"]

                if tool_name not in available_tool_names:
                    raise ValueError(
                        f"Unknown MCP tool selected: {tool_name}"
                    )

                if not isinstance(decision_data["arguments"], dict):
                    raise ValueError(
                        "Tool arguments must be a dictionary."
                    )

            elif decision_data["action"] == "final":

                if not decision_data["response"].strip():
                    decision_data["response"] = (
                        "I could not determine a reliable solution. "
                        "Please provide more details about the issue."
                    )

                decision_data["tool_name"] = ""
                decision_data["arguments"] = {}

            # -------------------------------------------------
            # 7. Record decision and token usage
            # -------------------------------------------------
            raw_response = llm_result.get("raw")

            usage = (
                getattr(raw_response, "usage_metadata", None) or {}
            )

            token_usage = {
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0),
            }

            state["messages"].append({
                "role": "assistant",
                "content": decision_data,
            })

            state["step_count"] += 1

            span.update(
                output={
                    "decision": decision_data,
                    "step_count": state["step_count"],
                },
                metadata={
                    "model": "openai/gpt-oss-20b",
                    "available_mcp_tools": sorted(
                        available_tool_names
                    ),
                    "error_recovery_attempt": bool(previous_error),
                    "status": "success",
                    "token_usage": token_usage,
                },
            )

            return state

        except Exception as exc:
            logger.exception("Reasoning node failed.")

            span.update(
                output={
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:1000],
                },
                metadata={
                    "status": "error",
                },
            )

            raise