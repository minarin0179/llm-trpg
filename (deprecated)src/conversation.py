import os
import requests
import autogen
from autogen import ConversableAgent, register_function
from dotenv import load_dotenv

load_dotenv()

llm_config = {
    "cache_seed": 42,  # change the cache_seed for different trials
    "temperature": 0,
    "config_list": [
        {
            "model": "gpt-4o",
            "temperature": 1.0,
            "api_key": os.environ["OPENAI_API_KEY"],
        }
    ],
    "timeout": 120,
}


user_proxy = autogen.UserProxyAgent(
    name="Minari",
    system_message="Minari.李研究室に属する生徒です．他の参加者と対話し，自身の研究について議論をしたいと思っています",
    code_execution_config=False,
)
professor = autogen.AssistantAgent(
    name="Professor_Lee",
    llm_config=llm_config,
    system_message="""Professor Lee．あなたは名古屋工業大学で研究室を構える教授です．生徒の研究の内容について，専門的な知見を踏まえてアドバイスをする必要があります""",
)
senior_1 = autogen.AssistantAgent(
    name="Sakai",
    llm_config=llm_config,
    system_message="""Sakai．あなたは李研究室の学生で，箕成の先輩です．研究の内容について，自身の知見をもとにアドバイスをする必要があります．あなた自身の研究の内容は「物語の要約」です""",
)

senior_2 = autogen.AssistantAgent(
    name="Kaneko",
    llm_config=llm_config,
    system_message="""Kaneko．あなたは李研究室の学生で，箕成の先輩です．研究の内容について，自身の知見をもとにアドバイスをする必要があります．あなた自身の研究の内容は「動機付け面接」です""",
)

senior_3 = autogen.AssistantAgent(
    name="Saito",
    llm_config=llm_config,
    system_message="""Saito．あなたは李研究室の学生で，箕成の先輩です．研究の内容について，自身の知見をもとにアドバイスをする必要があります．あなた自身の研究の内容は「人物関係図抽出」です""",
)
groupchat = autogen.GroupChat(
    agents=[user_proxy, professor, senior_1, senior_2, senior_3],
    messages=[],
    max_round=50,
)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

user_proxy.initiate_chat(
    manager,
    message="""
それでは本日のミーティングを始めてよろしいでしょうか？
""",
)
