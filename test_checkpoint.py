from disk_checkpoint import save_checkpoint, load_checkpoint


thread_id = "task7-test"

state = {
    "messages": [
        {
            "role": "user",
            "content": "My WiFi is not working"
        }
    ],
    "issue": "My WiFi is not working",
    "tool_results": [],
    "step_count": 3,
    "approval_status": "not_required",
}


# Save state to disk
save_checkpoint(thread_id, state)

print("CHECKPOINT SAVED")


# Load state back from disk
restored_state = load_checkpoint(thread_id)

print("CHECKPOINT RESTORED")
print(restored_state)


# Verify persistence
assert restored_state == state

print("DISK CHECKPOINT TEST PASSED")