from state import AgentState
from reasoning import reasoning_node
from agent_tools import run_tool_from_decision


def main():
    state: AgentState = {
        "messages": [],
        "issue": "Calculate 25 multiplied by 4.",
        "tool_results": [],
        "step_count": 0,
        "approval_status": "not_required",
    }

    print("=" * 50)
    print("IT SUPPORT AGENT - ERROR RECOVERY TEST")
    print("=" * 50)

    # Step 1: Deliberately introduce an invalid tool request.
    print("\nSTEP 1: Sending an invalid calculator request...")

    state["messages"].append({
        "role": "assistant",
        "content": {
            "action": "tool",
            "tool_name": "calculator_tool",
            "arguments": {},
            "response": "",
        },
    })

    state = run_tool_from_decision(state)

    print("Initial tool result:")
    print(state["tool_results"][-1])

    # Step 2: Ask the reasoning node to recover from the error.
    print("\nSTEP 2: Asking the reasoning node to recover...")

    state = reasoning_node(state)

    decision = state["messages"][-1]["content"]

    print("Recovery decision:")
    print(decision)

    # Step 3: Execute the corrected request if the model selected a tool.
    if decision.get("action") == "tool":
        print("\nSTEP 3: Executing the recovery decision...")

        state = run_tool_from_decision(state)

        print("Recovery result:")
        print(state["tool_results"][-1])

    else:
        print("\nThe model selected a final response instead of a tool.")
        print("Response:", decision.get("response", ""))

    print("\n" + "=" * 50)
    print("ERROR RECOVERY TEST FINISHED")
    print("Total steps:", state["step_count"])
    print("=" * 50)


if __name__ == "__main__":
    main()