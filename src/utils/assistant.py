
class Assistant:
    def __init__(self, instruction):
        self.instruction = instruction

    def init_history(self):
        self.history = [
            {
                "role": "system",
                "content": self.instruction}
        ]

    def add_message(self, message):
        self.history.append(message)
