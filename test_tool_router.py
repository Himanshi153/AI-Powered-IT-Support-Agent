from json_rpc import create_tool_request
from tool_router import execute_tool_request


request = create_tool_request(
    "troubleshoot_issue",
    {"issue": "My laptop is running very slowly"}
)

response = execute_tool_request(request)

print("JSON-RPC TROUBLESHOOT RESPONSE:")
print(response)