import os, requests
from dotenv import load_dotenv
from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager, register_function
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

# print("なんのシステムで遊びますか？ex) クトゥルフ神話TRPG，エモクロアTRPG")
# system = input()


SCENARIO_PATH = "scenario/hasshakusama_scenario.txt"
scenario_text = "シナリオの内容は以下の通りです．\n"
with open(SCENARIO_PATH, 'r', encoding='utf-8') as file:
    scenario_text = file.read()

CHARACTER_PATH = "character/hibiki.txt"

character_text = "プレイヤーのキャラクターの情報は以下の通りです.\n"
with open(CHARACTER_PATH, 'r', encoding='utf-8') as file:
    character_text = file.read()

RULEBOOK_PATH = "rulebook/emoklore.txt"
with open(RULEBOOK_PATH, 'r', encoding='utf-8') as file:
    rulebook_text = file.read()


llm_config = {"model": "gpt-4o", "api_key": os.environ["OPENAI_API_KEY"]}

shared_prompt = f"""
回答は常に日本語でお願いします．
"""

game_master_prompt = f"""
あなたはTRPGのゲームマスターです.
今から{system}のシナリオを一緒に遊びましょう．
あなたの他にも複数のGMが居るので彼らと相談しながら，
GM達の意見を取りまとめてあなたが総意をプレイヤーに伝えてください．
{scenario_text}
{character_text}
{shared_prompt}
"""

game_master = AssistantAgent(
    "GameMaster",
    system_message=game_master_prompt,
    llm_config=llm_config,
    human_input_mode="NEVER"
)

player_prompt = '''
あなたはTRPGのプレイヤーです.
ゲームに積極的に参加し，時には意思決定やダイスロールを行いながら物語のゴールを目指してください．
'''

player = UserProxyAgent(
    name="Player",
    system_message=player_prompt,
    human_input_mode="ALWAYS",
    llm_config=llm_config
)

rule_agent_prompt = """
あなたはTRPGのゲームマスターを補助する役割を任されています.
あなたはゲームのルールに特化した専門家として呼ばれています．
プレイヤーの入力に対して関連するルールがルールブックに記載されている場合はそれをゲームマスターが分かるように補足してください．
使用するゲームは{system}です．
ルールブックの内容は以下の通りです.
{rulebook_text}
{shared_prompt}
"""

rule_agent = AssistantAgent(
    "RuleAgent",
    system_message=rule_agent_prompt,
    llm_config=llm_config,
    human_input_mode="NEVER"
)

story_agent_prompt = f"""
あなたはTRPGのゲームマスターを補助する役割を任されています.
あなたはゲームのシナリオ進行に特化した専門家として呼ばれています．
ゲームにおけるシナリオ状況を把握し，プレイヤーの行おうとしている行動がシナリオ進行から大きく外れていないかをゲームマスターに補足してください．
また，次に取ることのできる行動やシナリオ進行の指針をゲームマスターに対して補足してください．
{scenario_text}
"""

story_agent = AssistantAgent(
    "StoryAgent",
    system_message=story_agent_prompt,
    llm_config=llm_config,
    human_input_mode="NEVER"
)

worldview_agent_prompt = f"""
あなたはTRPGのゲームマスターを補助する役割を任されています.
あなたはゲームの世界観説明や描写に特化した専門家として呼ばれています．
プレイヤーの行動が世界観や設定と矛盾がないかを判断してゲームマスターに補足してください．
{scenario_text}
"""

worldview_agent =  AssistantAgent(
    "WorldviewAgent",
    system_message=worldview_agent_prompt,
    llm_config=llm_config,
    human_input_mode="NEVER",
)


groupchat = GroupChat(
    agents=[game_master, rule_agent,story_agent,worldview_agent],
    messages=[],
    max_round=5,
)
manager = GroupChatManager(groupchat=groupchat, llm_config=llm_config)


register_function(
    die_roll,
    caller=game_master, 
    executor=player, 
    **die_roll_schema
)

def reflection_message(recipient, messages, sender, config):
    print("Reflecting...", "yellow")
    ans = f"""
以下のプレイヤーの行動に関連するルールはありますか？
プレイヤーの行動が含まれない場合は特にないと答えてください
ルールが存在する場合はそれについて関連するルールを説明してください．

{recipient.chat_messages_for_summary(sender)[-1]['content']}
    """
    return ans

nested_chats = [
    {
        "recipient": rule_agent,
        "summary_method": "reflection_with_llm",
        "message":reflection_message,
        "max_turns":1
    },
    # {
    #     "recipient": story_agent,
    #     "summary_method": "reflection_with_llm",
    #     "max_turns":2
    # },
    # {
    #     "recipient": worldview_agent,
    #     "summary_method": "reflection_with_llm",
    #     "max_turns":2
    # },
    # {
    #     "recipient": groupchat,
    #     "summary_method": "reflection_with_llm",
    #     "max_turns":3
    # }
]

game_master.register_nested_chats(
    nested_chats,
    trigger=lambda sender: sender not in [rule_agent],
)

player.initiate_chat(
    game_master,
    message="観察眼の技能で周囲を見渡してみます",
)


