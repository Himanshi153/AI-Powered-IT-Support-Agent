import json


def create_tool_request(tool_name: str, arguments: dict) -> dict:
    """Create a JSON-RPC 2.0 request for a tool call."""

    return {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {
            "name": tool_name,
            "arguments": arguments,
        },
        "id": 1,
    }


def serialize_request(request: dict) -> str:
    """Convert the JSON-RPC request to a JSON string."""

    return json.dumps(request)