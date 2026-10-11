from json_rpc import create_tool_request, serialize_request


request = create_tool_request(
    "calculator",
    {
        "expression": "25 * 4"
    }
)


print("JSON-RPC REQUEST:")
print(serialize_request(request))