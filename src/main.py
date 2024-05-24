import os, requests
from dotenv import load_dotenv
from autogen import AssistantAgent, UserProxyAgent, ConversableAgent
load_dotenv()


llm_config = {"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}
assistant = AssistantAgent("assistant", llm_config=llm_config)
user_proxy = UserProxyAgent("user_proxy", code_execution_config=False)

GM = ConversableAgent(
    "GM",
    # system_message="あなたはTRPGのゲームマスターです.ゲームを進行してください.",
    system_message="あなたはしりとりのプレイヤーです",
    llm_config={"config_list": [{"model": "gpt-4o", "temperature": 0.1, "api_key": os.environ.get("OPENAI_API_KEY")}]},
    human_input_mode="NEVER",  # Never ask for human input.
)

PL = ConversableAgent(
    "PL",
    # system_message="あなたはTRPGのプレイヤーです.ゲームマスターに質問してください.",
    system_message="あなたはしりとりのプレイヤーです",
    llm_config={"config_list": [{"model": "gpt-4o", "temperature": 0.1, "api_key": os.environ.get("OPENAI_API_KEY")}]},
    human_input_mode="NEVER",  # Never ask for human input.
)

result = GM.initiate_chat(PL, message="しりとりしてください.最初の言葉は「しらす」です.返答は単語だけでいいです", max_turns=10)
