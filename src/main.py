import json
from openai import OpenAI
from dotenv import load_dotenv
from typing_extensions import override
from openai import AssistantEventHandler
from utils.diceroll import diceroll_tool, Dicebot
from utils.file import read_text_file
from utils.openai_utils import get_history
from utils.io import user_input

load_dotenv()
client = OpenAI()

system = "エモクロアTPRG"

dicebot = Dicebot("Emoklore")

SCENARIO_PATH = "scenario/hasshakusama_scenario.txt"
scenario_text = f"シナリオの内容は以下の通りです．\n{read_text_file(SCENARIO_PATH)}"

CHARACTER_PATH = "character/hibiki.txt"

character_text = f"プレイヤーのキャラクターの情報は以下の通りです.\n{read_text_file(CHARACTER_PATH)}"

RULEBOOK_PATH = "rulebook/emoklore.txt"
rulebook_text = f"ルールブックの内容は以下の通りです.\n{read_text_file(RULEBOOK_PATH)}"

tools = [
    DICEROOL_TOOL
]

shared_prompt = f"""
回答は常に日本語でお願いします．
"""

GM_instruction = f"""
あなたはTRPGのゲームマスターです.
今から{system}のシナリオを一緒に遊びましょう．
{scenario_text}
{character_text}
{shared_prompt}
"""


messages = [
    {"role": "system", "content": GM_instruction},
    {"role": "user", "content": "セッションを始めましょう"},
]


def generate_response():
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
    )
    message = response.choices[0].message

    messages.append(message)

    if message.content:
        print(message.content)

    return response


response = generate_response()

while True:
    user_input_text = user_input()
    messages.append({"role": "user", "content": user_input_text})

    response = generate_response()

    tool_call = response.choices[0].message.tool_calls[0]

    if tool_call and tool_call.function.name == "diceroll":
        arguments = json.loads(tool_call.function.arguments)
        command = arguments.get("command")

        diceroll_result = dicebot.exec(command)
        print(diceroll_result)

        func_result = {
            "role": "tool",
            "content": json.dumps(diceroll_result),
            "tool_call_id": response.choices[0].message.tool_calls[0].id,
        }

        messages.append(func_result)

        response = generate_response()


# TODO エラーで中断した時用にmessagesを保存して再開する仕組みを作る
