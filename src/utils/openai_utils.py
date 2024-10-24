def get_history(client, thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return [{
        "role": message.role,
        "content": message.content[0].text.value,
    } for message in messages][::-1]


def switch_role(history,):
    new_history = history.copy()
    for message in new_history:
        if message["role"] == "user":
            message["role"] = "assistant"
        elif message["role"] == "assistant":
            message["role"] = "user"

    return new_history
