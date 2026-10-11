from mcp.server.mcpserver import MCPServer

from tools import calculator, get_system_info, troubleshoot_issue


server = MCPServer("IT Support Tools")


@server.tool()
def calculator_tool(expression: str) -> str:
    """Calculate a basic mathematical expression."""
    return calculator(expression)


@server.tool()
def get_system_info_tool() -> str:
    """Get basic read-only information about the computer."""
    return get_system_info()


@server.tool()
def troubleshoot_issue_tool(issue: str) -> str:
    """Provide safe troubleshooting guidance for a user's IT issue."""
    return troubleshoot_issue(issue)


if __name__ == "__main__":
    server.run(transport="stdio")