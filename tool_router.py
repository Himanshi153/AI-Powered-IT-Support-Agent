from tools import calculator, get_system_info, troubleshoot_issue

def execute_tool_request(request: dict) -> dict:
    """Execute a tool from a JSON-RPC request."""

    tool_name = request["params"]["name"]
    arguments = request["params"]["arguments"]

    if tool_name == "calculator":
        result = calculator(**arguments)

        return {
            "jsonrpc": "2.0",
            "result": {
                "tool": tool_name,
                "output": result,
            },
            "id": request["id"],
        }
    if tool_name == "get_system_info":
            result = get_system_info()
    
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tool": tool_name,
                    "output": result,
                },
                "id": request["id"],
            }
    if tool_name == "troubleshoot_issue":
            result = troubleshoot_issue(**arguments)
    
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tool": tool_name,
                    "output": result,
                },
                "id": request["id"],
            }
    
    return {
        "jsonrpc": "2.0",
        "error": {
            "code": -32601,
            "message": f"Tool not found: {tool_name}",
        },
        "id": request["id"],
    }