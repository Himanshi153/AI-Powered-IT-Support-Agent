import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


SERVER_PATH = Path(__file__).parent / "mcp_server.py"


async def discover_mcp_tools():
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH)],
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:

            await session.initialize()

            tools_result = await session.list_tools()

            tool_registry = []

            for tool in tools_result.tools:
                tool_registry.append(
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    }
                )

            return tool_registry
async def call_mcp_tool(tool_name: str, arguments: dict):
    server_params = StdioServerParameters(
        command=str(Path(__file__).parent / ".venv" / "Scripts" / "python.exe"),
        args=[str(SERVER_PATH)],
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:

            await session.initialize()

            result = await session.call_tool(
                tool_name,
                arguments
            )

            return result

async def main():
    result = await call_mcp_tool(
        "troubleshoot_issue_tool",
        {"issue": "My laptop is running very slowly"}
    )

    print("MCP EXECUTION RESULT:")
    print(result.content)

if __name__ == "__main__":
    asyncio.run(main())