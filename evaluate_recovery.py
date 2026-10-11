import json
import os
from pathlib import Path

from dotenv import load_dotenv
from langfuse import get_client
from langchain_groq import ChatGroq

load_dotenv(override=True)

MODEL_NAME = "openai/gpt-oss-20b"
OUTPUT_FILE = "recovery_evaluation_results.json"
OBSERVATIONS_TO_FETCH = 100
TARGET_EVALUATIONS = 3

api_key = os.getenv("GROQ_API_KEY")
if not api_key:
    raise ValueError("GROQ_API_KEY is missing from .env")

langfuse = get_client()
judge = ChatGroq(
    model=MODEL_NAME,
    temperature=0,
    api_key=api_key,
)


def as_dict(value):
    """Convert a dictionary or JSON string to a dictionary."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def observation_to_text(value):
    """Safely display and normalize observation input/output."""
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {"text": value}
    if value is None:
        return {}
    return {"text": str(value)}


def has_error(data):
    """Detect JSON-RPC errors in an observation."""
    if not isinstance(data, dict):
        return False
    if isinstance(data.get("error"), dict):
        return True
    output = data.get("output")
    return isinstance(output, dict) and isinstance(output.get("error"), dict)


def has_recovery_flag(metadata):
    return isinstance(metadata, dict) and metadata.get("error_recovery_attempt") is True


def is_relevant_observation(item):
    """Select error observations and reasoning observations explicitly marked as recovery."""
    return (
        has_error(item["output"])
        or has_recovery_flag(item["metadata"])
    )


def judge_recovery(record):
    """Ask the LLM judge to score one historical observation, without inventing evidence."""
    prompt = f"""
You are an independent evaluator of an IT Support Agent's error recovery.

Evaluate ONLY the evidence in this single Langfuse observation.
This observation may be only one part of a larger recovery sequence.
Do not assume that missing events happened, and do not claim successful
recovery unless this observation itself establishes it.

Evidence:
{json.dumps(record, indent=2, ensure_ascii=False, default=str)}

Use an integer score from 1 to 5:
1 = Error is present, but this observation shows no recovery attempt.
2 = Error was recognized, but the correction shown is ineffective.
3 = A correction was attempted, but success is not established here.
4 = This observation provides evidence of a corrected request succeeding.
5 = This observation alone clearly establishes error detection, correction,
    and a verified successful result.

If this single observation does not provide enough evidence, score it
conservatively and explain the limitation. Do not treat a successful
standalone request as proof of error recovery.

Return ONLY valid JSON with these keys:
{{
  "score": 1,
  "error_detected": false,
  "recovery_attempted": false,
  "recovery_successful": false,
  "reason": "Evidence-based explanation"
}}
"""
    response = judge.invoke(prompt)
    content = response.content

    if isinstance(content, list):
        content = "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )

    content = str(content).strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    result = json.loads(content)
    score = result.get("score")
    if not isinstance(score, int) or not 1 <= score <= 5:
        raise ValueError(f"Invalid judge score: {score}")
    return result


def main():
    print("Fetching Langfuse observations...")

    response = langfuse.api.observations.get_many(
        limit=OBSERVATIONS_TO_FETCH,
        fields="core,io,metadata",
    )

    observations = []
    for observation in response.data:
        observations.append({
            "observation_id": getattr(observation, "id", None),
            "trace_id": getattr(observation, "trace_id", None),
            "name": getattr(observation, "name", None),
            "input": observation_to_text(getattr(observation, "input", None)),
            "output": observation_to_text(getattr(observation, "output", None)),
            "metadata": getattr(observation, "metadata", None) or {},
        })

    if not observations:
        print("No observations found in Langfuse.")
        return

    print("\n--- RECENT OBSERVATIONS (DEBUG) ---")
    for item in observations:
        print(
            json.dumps(
                {
                    "observation_id": item["observation_id"],
                    "trace_id": item["trace_id"],
                    "name": item["name"],
                    "input": item["input"],
                    "output": item["output"],
                    "metadata": item["metadata"],
                },
                ensure_ascii=False,
                default=str,
            )[:1800]
        )
    print("--- END OBSERVATION DEBUG ---\n")

    candidates = [item for item in observations if is_relevant_observation(item)]
    selected = candidates[:TARGET_EVALUATIONS]

    print("Historical observations found:", len(observations))
    print("Observations with relevant error/recovery evidence:", len(candidates))
    print("Records selected for evaluation:", len(selected))

    results = []
    for index, item in enumerate(selected, start=1):
        record = {
            "observation_id": item["observation_id"],
            "trace_id": item["trace_id"],
            "name": item["name"],
            "input": item["input"],
            "output": item["output"],
            "metadata": item["metadata"],
        }
        print(f"\nEvaluating observation {index}/{len(selected)}...")
        try:
            evaluation = judge_recovery(record)
            results.append({
                "record_number": index,
                "evidence": record,
                "evaluation": evaluation,
            })
            print("Score:", evaluation["score"])
            print("Reason:", evaluation["reason"])
        except Exception as exc:
            print(f"Judge failed: {type(exc).__name__}: {exc}")

    output_path = Path(OUTPUT_FILE)
    output_path.write_text(
        json.dumps(
            {
                "model": MODEL_NAME,
                "evaluation_method": "LLM-as-a-judge",
                "scoring_scale": "1-5",
                "target_evaluations": TARGET_EVALUATIONS,
                "historical_observations_found": len(observations),
                "relevant_observations_found": len(candidates),
                "successfully_evaluated_observations": len(results),
                "note": (
                    "These are individual observations, not necessarily complete "
                    "end-to-end recovery episodes. Do not interpret the average "
                    "as an overall agent performance score."
                ),
                "results": results,
            },
            indent=2,
            ensure_ascii=False,
            default=str,
        ),
        encoding="utf-8",
    )

    print("\n========== EVALUATION SUMMARY ==========")
    print("Records successfully evaluated:", len(results))
    print("Target evaluations:", TARGET_EVALUATIONS)
    if len(results) < TARGET_EVALUATIONS:
        print("NOTE: Fewer than 3 relevant historical observations were evaluated.")
    if results:
        scores = [entry["evaluation"]["score"] for entry in results]
        print("Average observation score:", round(sum(scores) / len(scores), 2))
        print("Reminder: individual-observation average is not an end-to-end recovery score.")
    print("Saved:", output_path.resolve())

    langfuse.flush()


if __name__ == "__main__":
    main()
