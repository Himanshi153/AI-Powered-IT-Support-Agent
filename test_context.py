from context_manager import compact_messages


class DummySummarizer:
    def invoke(self, prompt):
        return type(
            "Response",
            (),
            {
                "content": "User reported several IT issues and previous troubleshooting steps were discussed."
            },
        )()


messages = [
    {"role": "user", "content": "Message 1: My laptop is slow."},
    {"role": "assistant", "content": "Message 2: Let's check system usage."},
    {"role": "user", "content": "Message 3: CPU usage is high."},
    {"role": "assistant", "content": "Message 4: Check Task Manager."},
    {"role": "user", "content": "Message 5: I checked Task Manager."},
    {"role": "assistant", "content": "Message 6: Check startup applications."},
    {"role": "user", "content": "Message 7: I found some unnecessary apps."},
    {"role": "assistant", "content": "Message 8: Disable unnecessary startup apps."},
    {"role": "user", "content": "Message 9: I disabled them."},
    {"role": "assistant", "content": "Message 10: Check disk space."},
    {"role": "user", "content": "Message 11: Disk space is sufficient."},
    {"role": "assistant", "content": "Message 12: The laptop is still slow."},
]


result = compact_messages(
    messages,
    DummySummarizer()
)


print("ORIGINAL MESSAGE COUNT:", len(messages))
print("COMPACTED MESSAGE COUNT:", len(result))
print("\nCOMPACTED MESSAGES:")

for message in result:
    print(message)