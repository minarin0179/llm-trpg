import os
import requests
from autogen import ConversableAgent,register_function
from dotenv import load_dotenv
load_dotenv()

def die_roll(command: str) -> dict:
    
    params = {
        "command": command
    }
    id="Emoklore"

    response = requests.get(f"{os.environ["BCDICE_API_URL"]}/v2/game_system/{id}/roll", params=params)
    result = response.json()
    return result

die_roll_schema = {
    "name":"die_roll",
    "description":"Execute a die roll. BCDice is used for die rolls. If a die roll is requested, find the appropriate die roll in the chat palette and output it as a command. If there is no command in the chat palette and a command is explicitly given, execute it. If none of the above apply, there is no need to execute the command."
}


llm_config = {
    "config_list": [
        {
            "model": "gpt-4o",
            "temperature": 1.0,
            "api_key": os.environ["OPENAI_API_KEY"],
        }
    ]
}

assistant = ConversableAgent(
    name="TRPG Game Master Assistant",
    system_message="You are an excellent TPRG game master. I will tell you the rules and scenarios to use and we will start the session together! Conversations will be conducted in Japanese. Do not give too much advice or hints in order to encourage positive action from the player. Keep the session on track with the scenario, and if things get too far off-topic, let the conversation naturally pick up where it left off. You know all the details of the scenario, but players do not know the scenario, so use your best efforts not to spoil it for them. Reveal core information about the scenario gradually during the session. You do not need to explain the rules unless asked to do so. Please do your best to avoid making up content that is not included in the scenario. When speaking to me as an NPC, please end the conversation with the NPC's lines so that I can respond as a character.",
    llm_config=llm_config,
)

user_proxy = ConversableAgent(
    name="User",
    llm_config=False,
    is_termination_msg=lambda msg: msg.get("content") is not None
    and "TERMINATE" in msg["content"],
    human_input_mode="ALWAYS",
)

register_function(
    die_roll,
    caller=assistant, 
    executor=user_proxy, 
    **die_roll_schema
)
chat_result = user_proxy.initiate_chat(assistant, message="2d6をダイスロールしてください。")
