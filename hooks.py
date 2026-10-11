from typing import Dict, Any


def pre_tool_hook(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a tool request before it is sent to the MCP server.
    """

    allowed_tools = {
        "calculator_tool",
        "get_system_info_tool",
        "troubleshoot_issue_tool",
    }

    # Tool existence validation
    if tool_name not in allowed_tools:
        return {
            "valid": False,
            "status_code": 400,
            "error": f"Unknown tool: {tool_name}",
        }

    # Argument validation
    if tool_name == "calculator_tool":
        if "expression" not in arguments or not arguments["expression"]:
            return {
                "valid": False,
                "status_code": 400,
                "error": "calculator_tool requires 'expression'.",
            }

    elif tool_name == "troubleshoot_issue_tool":
        if "issue" not in arguments or not arguments["issue"]:
            return {
                "valid": False,
                "status_code": 400,
                "error": "troubleshoot_issue_tool requires 'issue'.",
            }

    elif tool_name == "get_system_info_tool":
        if arguments:
            return {
                "valid": False,
                "status_code": 400,
                "error": "get_system_info_tool does not accept arguments.",
            }

    return {
        "valid": True,
        "status_code": 200,
        "error": None,
    }


def post_tool_hook(
    tool_name: str,
    arguments: Dict[str, Any],
    result: Any,
) -> Dict[str, Any]:
    """
    Process and validate the result after a tool execution.
    """

    return {
        "tool_name": tool_name,
        "arguments": arguments,
        "result": result,
        "status": "success",
    }