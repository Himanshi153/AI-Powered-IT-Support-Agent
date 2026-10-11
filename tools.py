from typing import Any


calculator_schema = {
    "name": "calculator",
    "description": "Calculate a basic mathematical expression.",
    "input_schema": {
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression to calculate."
            }
        },
        "required": ["expression"]
    }
}


def calculator(expression: str) -> str:
    """Calculate a basic mathematical expression."""

    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return str(result)
    except Exception as e:
        return f"Calculation error: {str(e)}"


system_info_schema = {
    "name": "get_system_info",
    "description": "Get basic read-only information about the computer.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}


def get_system_info() -> str:
    """Get basic read-only information about the computer."""

    import platform
    import os

    info = {
        "operating_system": platform.system(),
        "os_version": platform.version(),
        "computer_name": platform.node(),
        "cpu": platform.processor(),
        "cpu_count": os.cpu_count(),
    }

    return str(info)

troubleshoot_schema = {
    "name": "troubleshoot_issue",
    "description": "Provide safe troubleshooting guidance for a user's IT issue.",
    "input_schema": {
        "type": "object",
        "properties": {
            "issue": {
                "type": "string",
                "description": "The technical issue reported by the user."
            }
        },
        "required": ["issue"]
    }
}


def troubleshoot_issue(issue: str) -> str:
    """Provide basic troubleshooting guidance."""

    issue_lower = issue.lower()

    if "slow" in issue_lower or "lag" in issue_lower:
        return (
            "Recommended checks: review CPU and RAM usage in Task Manager, "
            "close unnecessary background applications, check startup programs, "
            "verify available disk space, and check for pending Windows updates."
        )

    if "internet" in issue_lower or "wifi" in issue_lower:
        return (
            "Recommended checks: verify Wi-Fi connection, restart the network "
            "adapter, restart the router if appropriate, and check whether "
            "other devices have the same connectivity issue."
        )

    if "blue screen" in issue_lower or "crash" in issue_lower:
        return (
            "Recommended checks: note the error code, check recent driver or "
            "software changes, run Windows diagnostics, and review system logs."
        )

    return (
        "Collect more information about the issue, including the exact error "
        "message, when it started, recent changes, and affected applications."
    )