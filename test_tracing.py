from tracing import trace_operation, flush_traces


@trace_operation("test_operation")
def sample_operation():
    return {
        "status": "success",
        "message": "Langfuse tracing test successful"
    }


if __name__ == "__main__":
    result = sample_operation()
    print("TEST RESULT:", result)

    flush_traces()
    print("TRACES FLUSHED")