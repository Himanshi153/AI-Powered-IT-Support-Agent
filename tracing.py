import time
from functools import wraps
from dotenv import load_dotenv
from langfuse import get_client

# Load environment variables before initializing Langfuse.
load_dotenv(override=True)

langfuse = get_client()


def trace_operation(name: str):
    """Record an operation as a Langfuse span."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.perf_counter()

            with langfuse.start_as_current_observation(
                as_type="span",
                name=name,
                input={
                    "function": func.__name__,
                    "args": repr(args)[:1000],
                    "kwargs": repr(kwargs)[:1000],
                },
            ) as span:
                try:
                    result = func(*args, **kwargs)

                    elapsed_ms = round(
                        (time.perf_counter() - start_time) * 1000, 2
                    )

                    span.update(
                        output={"result": repr(result)[:2000]},
                        metadata={
                            "status": "success",
                            "latency_ms": elapsed_ms,
                        },
                    )

                    print(f"[TRACE] {name}: {elapsed_ms} ms")
                    return result

                except Exception as exc:
                    elapsed_ms = round(
                        (time.perf_counter() - start_time) * 1000, 2
                    )

                    span.update(
                        output={"error": str(exc)},
                        metadata={
                            "status": "error",
                            "error_type": type(exc).__name__,
                            "latency_ms": elapsed_ms,
                        },
                    )
                    raise

        return wrapper

    return decorator


def flush_traces():
    """Flush queued telemetry to Langfuse."""
    langfuse.flush()