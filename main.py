import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from agent_graph import agent_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI-Powered IT Support Agent",
    description="An AI agent that troubleshoots IT issues using MCP tools.",
    version="1.0.0",
)


class IssueRequest(BaseModel):
    issue: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Describe the IT issue you want help with.",
    )


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/webhook")
def webhook(request: IssueRequest):
    issue = request.issue.strip()

    if not issue:
        raise HTTPException(
            status_code=400,
            detail="Please provide a valid IT issue.",
        )

    initial_state = {
        "messages": [],
        "issue": issue,
        "tool_results": [],
        "step_count": 0,
        "approval_status": "not_required",
    }

    try:
        result = agent_graph.invoke(initial_state)

        # Find the latest final response from the agent.
        response = None

        for message in reversed(result.get("messages", [])):
            content = message.get("content", {})

            if (
                message.get("role") == "assistant"
                and isinstance(content, dict)
                and content.get("action") == "final"
            ):
                response = content.get("response")
                break

        if not response:
            response = (
                "The agent could not produce a final response. "
                "Please try again."
            )

        return {
            "issue": issue,
            "response": response,
            "steps": result.get("step_count", 0),
            "tool_results": result.get("tool_results", []),
        }

    except Exception:
        logger.exception("IT support agent execution failed.")

        raise HTTPException(
            status_code=500,
            detail="The agent encountered an internal error. Please try again.",
        )