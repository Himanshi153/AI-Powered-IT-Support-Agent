from typing import List, Dict, Any


def compact_messages(
    messages: List[Dict[str, Any]],
    summarizer
) -> List[Dict[str, Any]]:
    """
    Compact conversation context when there are more than 10 messages.

    The first 8 messages are summarized and replaced
    with a single summary message.
    """

    # No compaction required
    if len(messages) <= 10:
        return messages

    # Take the first 8 messages for summarization
    old_messages = messages[:8]

    # Keep messages after the first 8
    remaining_messages = messages[8:]

    # Convert old messages into text
    conversation_text = "\n".join(
        [
            f"{message.get('role', 'unknown')}: "
            f"{message.get('content', '')}"
            for message in old_messages
        ]
    )

    # Ask the summarizer to create a compact context
    summary_prompt = f"""
Summarize the following IT support conversation context.

Preserve:
- the user's technical issue
- important troubleshooting information
- important tool results
- important decisions
- human approval or rejection information

Keep the summary concise but useful for future reasoning.

Conversation:
{conversation_text}
"""

    summary_response = summarizer.invoke(summary_prompt)

    if hasattr(summary_response, "content"):
        summary_text = summary_response.content
    else:
        summary_text = str(summary_response)

    # Replace the first 8 messages with one summary message
    summary_message = {
        "role": "system",
        "content": f"Context summary: {summary_text}",
    }

    return [summary_message] + remaining_messages