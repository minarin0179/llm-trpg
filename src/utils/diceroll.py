import os
import requests
from dotenv import load_dotenv
from typing import Dict, Any
load_dotenv()


DICEROOL_TOOL = {
    "type": "function",
    "function": {
            "name": "diceroll",
            "description": """This function executes a dice roll using the BCDice system.
The function processes die roll requests based on chat palette commands or explicit input from the user. 
- If the die roll can be found in the chat palette, extract and execute the relevant command.
- If no command is available in the chat palette and the user provides an explicit roll command, execute it as given.
- If the die roll requires a variable (e.g., a character's stat or modifier) enclosed in curly braces {}, refer to the dialogue history to retrieve and fill in the necessary value.
- If none of the above conditions are met, the die roll does not need to be executed.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The dice roll command that can be executed using BCDice."
                    }
                },
                "required": ["command"]
            }
        }
    }


class Dicebot:
    def __init__(self, id: str = "DiceBot"):
        system_info = requests.get(
            f"{os.environ["BCDICE_API_URL"]}/v2/game_system/{id}").json()

        if system_info["ok"] == False:
            raise ValueError(f"System {id} not found")

        self.id = id

    def exec(self, command: str) -> Dict[str, Any]:
        params = {
            "command": command
        }
        response = requests.get(
            f"{os.environ["BCDICE_API_URL"]}/v2/game_system/{self.id}/roll", params=params)
        result = response.json()
        return result


if __name__ == "__main__":
    dicebot = Dicebot()
    command = input("Enter command: ")

    print(dicebot.exec(command))
