import os, requests
from dotenv import load_dotenv
from typing import Dict,Any
load_dotenv()

def diceroll(command: str) -> Dict[str, Any]:
    params = {
        "command": command
    }
    id="Emoklore"
    response = requests.get(f"{os.environ["BCDICE_API_URL"]}/v2/game_system/{id}/roll", params=params)
    result = response.json()
    return result

# GM.register_for_llm(name=diceroll,description="bcdiceを使用してダイスロールを行います.")(diceroll)

# print(diceroll(input()))