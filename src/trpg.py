import os
import requests
from dotenv import load_dotenv
from autogen.agentchat.contrib.gpt_assistant_agent import GPTAssistantAgent
from autogen.function_utils import get_function_schema
from autogen import ConversableAgent, register_function

load_dotenv()

def die_roll(command: str) -> dict:
    
    return {result:"2d6 > 7"}
    """
    Execute a die roll.

    Args:
        command (str): Command that can be executable in Bcdice.

    Returns:
        dict: Dice roll result.
    """
    
    params = {
        "command": command
    }
    id="Emoklore"

    response = requests.get(f"{os.environ["BCDICE_API_URL"]}/v2/game_system/{id}/roll", params=params)
    result = response.json()
    return result

api_schema = get_function_schema(
    die_roll,
    name=die_roll.__name__,
    description="Execute a die roll. BCDice is used for die rolls. If a die roll is requested, find the appropriate die roll in the chat palette and output it as a command. If there is no command in the chat palette and a command is explicitly given, execute it. If none of the above apply, there is no need to execute the command."
)

llm_config = {
    "config_list": [
        {
            "model": "gpt-4o",
            "temperature": 1.0,
            "api_key": os.environ.get("OPENAI_API_KEY"),
        }
    ]
}
assistant_config = {
    "tools":[
        api_schema
    ]
}

args = {
    "name": "TRPG Game Master Assistant",
    "instructions": "You are an excellent TPRG game master. I will tell you the rules and scenarios to use and we will start the session together! Conversations will be conducted in Japanese. Do not give too much advice or hints in order to encourage positive action from the player. Keep the session on track with the scenario, and if things get too far off-topic, let the conversation naturally pick up where it left off. You know all the details of the scenario, but players do not know the scenario, so use your best efforts not to spoil it for them. Reveal core information about the scenario gradually during the session. You do not need to explain the rules unless asked to do so. Please do your best to avoid making up content that is not included in the scenario. When speaking to me as an NPC, please end the conversation with the NPC's lines so that I can respond as a character.",
    "llm_config": llm_config,
    "assistant_config": assistant_config,
}

oai_agent = GPTAssistantAgent(**args)

# oai_agent.register_function(
#     function_map={"die_roll": die_roll},
# )

human_proxy = ConversableAgent(
    "human_proxy",
    llm_config=False,  # no LLM used for human proxy
    human_input_mode="NEVER",  # always ask for human input
)

# oai_agent.register_for_llm(name="die_roll", function=die_roll)
# register_function(
#     die_roll,caller=oai_agent,executor=human_proxy,description="bcdiceを使用してダイスロールを行います."
# )

oai_agent.register_for_llm(name="die_roll", description="bcdiceを使用してダイスロールを行います.")(die_roll)

human_proxy.register_for_execution(name="die_roll")(die_roll)

result = human_proxy.initiate_chat(oai_agent, message="2d6をダイスロール")

# TODO: function callingの実装
# https://microsoft.github.io/autogen/docs/topics/openai-assistant/gpt_assistant_agent#function-calling

{
    "name": "diceroll",
    "description": "Execute a die roll. BCDice is used for die rolls. If a die roll is requested, find the appropriate die roll in the chat palette and output it as a command. If there is no command in the chat palette and a command is explicitly given, execute it. If none of the above apply, there is no need to execute the command.",
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Command that can be executable in Bcdice. ",
            }
        },
        "required": ["command"],
    },
}
