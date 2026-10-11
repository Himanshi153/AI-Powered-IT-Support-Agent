import json
import os
import re
from pathlib import Path

from dotenv import load_dotenv
from langchain_groq import ChatGroq

from state import AgentState
from reasoning import reasoning_node
from agent_tools import run_tool_from_decision


load_dotenv(override=True)

MODEL_NAME = "openai/gpt-oss-20b"
OUTPUT_FILE = "recovery_evaluation_results.json"

API_KEY = os.getenv("GROQ_API_KEY")

if not API_KEY:
    raise ValueError(
        "GROQ_API_KEY missing hai. Apni .env file check karo."
    )

judge = ChatGroq(
    model=MODEL_NAME,
    temperature=0,
    api_key=API_KEY,
)

TEST_CASES = [
    {
        "issue": "Calculate 25 multiplied by 4.",
        "expression": "25 * 4",
    },
    {
        "issue": "Calculate 18 plus 27.",
        "expression": "18 + 27",
    },
    {
        "issue": "Calculate 144 divided by 12.",
        "expression": "144 / 12",
    },
    {
        "issue": "Calculate 19 multiplied by 6.",
        "expression": "19 * 6",
    },
    {
        "issue": "Calculate 250 minus 85.",
        "expression": "250 - 85",
    },
    {
        "issue": "Calculate 16 multiplied by 7.",
        "expression": "16 * 7",
    },
    {
        "issue": "Calculate 81 divided by 9.",
        "expression": "81 / 9",
    },
    {
        "issue": "Calculate 125 plus 375.",
        "expression": "125 + 375",
    },
    {
        "issue": "Calculate 32 multiplied by 8.",
        "expression": "32 * 8",
    },
    {
        "issue": "Calculate 500 minus 175.",
        "expression": "500 - 175",
    },
]


def extract_json(text):
    """Extract JSON returned by the judge model."""
    text = str(text).strip()

    text = re.sub(
        r"^```(?:json)?\s*",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*```$", "", text)

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("Judge ne valid JSON return nahi kiya.")

    return json.loads(text[start:end + 1])


def evaluate_case(record):
    prompt = f"""
You are an independent evaluator of an IT Support Agent.

Evaluate this COMPLETE error-recovery test case:

{json.dumps(record, indent=2, ensure_ascii=False, default=str)}

Use this integer scoring rubric:

1 = Error occurred; no meaningful recovery.
2 = Recovery attempted but correction was ineffective.
3 = Corrected request attempted; success is not established.
4 = Corrected request succeeded.
5 = Error was detected, the request was corrected, and the
    successful result is verified by the recorded evidence.

Only use the evidence provided. Do not invent missing events.
A successful result must belong to the recovery attempt.
If recovery failed, score it honestly.

Return ONLY valid JSON in this format:
{{
  "score": 1,
  "error_detected": true,
  "recovery_attempted": true,
  "recovery_successful": false,
  "reason": "Evidence-based explanation"
}}
"""

    response = judge.invoke(prompt)
    result = extract_json(response.content)

    score = result.get("score")

    if not isinstance(score, int) or not 1 <= score <= 5:
        raise ValueError(f"Invalid judge score: {score}")

    return result


def run_test(test_number, test_case):
    print(f"\n{'=' * 55}")
    print(f"TEST {test_number}/10")
    print("Issue:", test_case["issue"])

    state: AgentState = {
        "messages": [],
        "issue": test_case["issue"],
        "tool_results": [],
        "step_count": 0,
        "approval_status": "not_required",
    }

    # Deliberately introduce a validation error.
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
    initial_error = state["tool_results"][-1]

    print("Initial error recorded.")

    # Ask the reasoning node to recover.
    state = reasoning_node(state)
    recovery_decision = state["messages"][-1]["content"]

    print("Recovery decision:", recovery_decision)

    recovery_result = None

    if recovery_decision.get("action") == "tool":
        state = run_tool_from_decision(state)
        recovery_result = state["tool_results"][-1]
        print("Recovery result:", recovery_result)
    else:
        print("Model returned a final response instead of a tool call.")

    return {
        "test_number": test_number,
        "issue": test_case["issue"],
        "expected_expression": test_case["expression"],
        "initial_error": initial_error,
        "recovery_decision": recovery_decision,
        "recovery_result": recovery_result,
        "step_count": state["step_count"],
    }


def main():
    records = []

    print("=" * 55)
    print("IT SUPPORT AGENT - 10 CASE RECOVERY EVALUATION")
    print("=" * 55)

    # Run and save each genuine test case.
    for number, test_case in enumerate(TEST_CASES, start=1):
        try:
            record = run_test(number, test_case)
            records.append(record)
        except Exception as exc:
            print(
                f"Test {number} failed: "
                f"{type(exc).__name__}: {exc}"
            )

        # Save progress so completed cases are not lost.
        Path(OUTPUT_FILE).write_text(
            json.dumps(
                {
                    "model": MODEL_NAME,
                    "target_cases": len(TEST_CASES),
                    "completed_tests": records,
                    "evaluations": [],
                },
                indent=2,
                ensure_ascii=False,
                default=str,
            ),
            encoding="utf-8",
        )

    if not records:
        print("\nNo test cases completed. Check the error messages.")
        return

    # Ask the LLM judge to evaluate each complete test record.
    evaluations = []

    print("\n" + "=" * 55)
    print("LLM-AS-A-JUDGE EVALUATION")
    print("=" * 55)

    for index, record in enumerate(records, start=1):
        print(f"\nJudging case {index}/{len(records)}...")

        try:
            evaluation = evaluate_case(record)

            evaluations.append({
                "test_number": record["test_number"],
                "evaluation": evaluation,
            })

            print("Score:", evaluation["score"])
            print("Reason:", evaluation["reason"])

        except Exception as exc:
            print(
                f"Judge failed for case {index}: "
                f"{type(exc).__name__}: {exc}"
            )

    valid_scores = [
        item["evaluation"]["score"]
        for item in evaluations
    ]

    report = {
        "model": MODEL_NAME,
        "evaluation_method": "LLM-as-a-judge",
        "scoring_scale": "1-5",
        "target_cases": len(TEST_CASES),
        "completed_test_cases": len(records),
        "successfully_evaluated_cases": len(evaluations),
        "average_score": (
            round(sum(valid_scores) / len(valid_scores), 2)
            if valid_scores else None
        ),
        "completed_tests": records,
        "evaluations": evaluations,
    }

    Path(OUTPUT_FILE).write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    print("\n" + "=" * 55)
    print("FINAL SUMMARY")
    print("=" * 55)
    print("Test cases completed:", len(records), "/ 10")
    print("Cases evaluated:", len(evaluations), "/", len(records))
    print("Average judge score:", report["average_score"])
    print("Report saved:", Path(OUTPUT_FILE).resolve())

    if len(records) < 10 or len(evaluations) < len(records):
        print(
            "NOTE: Kuch tests ya evaluations fail hue. "
            "Report mein sirf completed results count hue hain."
        )


if __name__ == "__main__":
    main()