import json
from pathlib import Path
from typing import Dict, Any


CHECKPOINT_FILE = Path(__file__).parent / "checkpoints.json"


def save_checkpoint(thread_id: str, state: Dict[str, Any]) -> None:
    """
    Persist agent state to disk using a JSON checkpoint file.
    """

    if CHECKPOINT_FILE.exists():
        try:
            data = json.loads(CHECKPOINT_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    data[thread_id] = state

    CHECKPOINT_FILE.write_text(
        json.dumps(data, indent=2, default=str),
        encoding="utf-8",
    )


def load_checkpoint(thread_id: str) -> Dict[str, Any] | None:
    """
    Load a previously persisted agent state from disk.
    """

    if not CHECKPOINT_FILE.exists():
        return None

    try:
        data = json.loads(
            CHECKPOINT_FILE.read_text(encoding="utf-8")
        )
    except json.JSONDecodeError:
        return None

    return data.get(thread_id)