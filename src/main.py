import json
from openai import OpenAI
from dotenv import load_dotenv
from utils.diceroll import DICEROOL_TOOL, Dicebot, show_diceroll_result
from utils.file import read_text_file
from utils.io import user_input
from utils.ansi import GRAY, RESET
from openai.types.chat.chat_completion import ChatCompletion

load_dotenv()
client = OpenAI()

GAME_SYSTEM = "エモクロアTPRG"

dicebot = Dicebot("Emoklore")

MAX_FEEDBACK = 3
DEBUG = True

SCENARIO_PATH = "scenario/hasshakusama_scenario.txt"
scenario_text = f"シナリオの内容は以下の通りです．\n{read_text_file(SCENARIO_PATH)}"

CHARACTER_PATH = "character/hibiki.txt"

# TODO: キャラクターの作成もセッション内で行うようにする
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
今から{GAME_SYSTEM}のシナリオを一緒に遊びましょう．
{scenario_text}
{character_text}
{shared_prompt}
"""

assistants = [
    """
    あなたはTRPGのゲームマスターの補佐役です.
    ゲームマスターである私のプレイヤーに対する，返信について問題がなければ「OK」とだけ返してください．
    問題点があれば，その問題点を具体的に指摘し，改善案を提案してください．
    ルールブックの内容は以下の通りです．
    {rulebook_text}
    """,
]

messages = [
    {"role": "system", "content": GM_instruction},
    {"role": "user", "content": "セッションを始めましょう"},
]


def stringfy_messages(messages: list[dict]) -> str:
    role_map = {
        "user": "Player",
        "system": "GM",
        "Assistant": "Assistant",
    }
    result = ""
    for m in messages:
        role = role_map.get(m.get("role"))
        content = m.get("content")
        result += f"{role} : {content}\n"
    return result


def debug_print(text):
    if DEBUG:
        print(f"{GRAY}{text}{RESET}")


def generate_debate_response() -> ChatCompletion:
    temporal_response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
    )

    message = temporal_response.choices[0].message

    tool_call = message.tool_calls[0] if message.tool_calls else None

    if tool_call and tool_call.function.name == "diceroll":
        arguments = json.loads(tool_call.function.arguments)
        command = arguments.get("command")

        diceroll_result = dicebot.exec(command)
        show_diceroll_result(diceroll_result)
        print("-"*30)

        func_result = {
            "role": "tool",
            "content": json.dumps(diceroll_result),
            "tool_call_id": temporal_response.choices[0].message.tool_calls[0].id,
        }
        # dicerollの際はtoolcallを履歴に追加
        messages.append(temporal_response.choices[0].message.to_dict())
        messages.append(func_result)

        # toolcallしたら結果を入れて続きの応答を生成
        return generate_debate_response()

    # main loop
    for i in range(MAX_FEEDBACK):
        debug_print(temporal_response.choices[0].message.content)
        feedbacks = []
        for assistant in assistants:
            temporal_messages = [
                {"role": "system", "content": assistant},
                {"role": "user", "content": f"以下は直前のGMとプレイヤーのやり取りです{
                    # messages[-2:]とtemporalresponseを結合してstringfyする
                    stringfy_messages(messages[-2:] + [temporal_response.choices[0].message.to_dict()])}"
                 },
            ]

            # TODO: feedbackを会話履歴に残すべきか検証

            feedback_response = client.chat.completions.create(
                model="gpt-4o",
                messages=temporal_messages,
                tools=tools,
            )

            debug_print(f"feedback{i} : {
                        feedback_response.choices[0].message.content}")
            # TODO: reasoningも含めて出力
            if feedback_response.choices[0].message.content == "OK":
                continue

            feedbacks.append(feedback_response)

        if not feedbacks:  # 全員がOKを出したら終了
            break
        # feedbackを踏まえてtemporalresponseを更新する
        temporal_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                *messages,
                temporal_response.choices[0].message,
                {"role": "user", "content": "前回の応答に対してフィードバックを与えるので，それらを踏まえて応答をやり直してください．"},
                *[{"role": "user", "content": f"feedback{i} : {feedback.choices[0].message}"}
                    for i, feedback in enumerate(feedbacks)],
            ],
            tools=tools,
        )
    return temporal_response


def generate_response(temporal: bool = False) -> ChatCompletion:

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
    )

    # toolcallがあった時はそれを履歴に入れずにその次の出力まで生成して返して欲しい

    if temporal:
        return response

    message = response.choices[0].message
    messages.append(message.to_dict())

    if message.content:
        print(f"GM : {message.content}")
        print("-"*30)

    tool_call = message.tool_calls[0] if message.tool_calls else None

    if tool_call and tool_call.function.name == "diceroll":
        arguments = json.loads(tool_call.function.arguments)
        command = arguments.get("command")

        diceroll_result = dicebot.exec(command)
        show_diceroll_result(diceroll_result)
        print("-"*30)

        func_result = {
            "role": "tool",
            "content": json.dumps(diceroll_result),
            "tool_call_id": response.choices[0].message.tool_calls[0].id,
        }

        messages.append(func_result)

        response = generate_response()

    return response


# initial response
response = generate_response()

while True:
    user_input_text = user_input()
    messages.append({"role": "user", "content": user_input_text})
    # response = generate_response()
    response = generate_debate_response()
    print(response.choices[0].message.content)

# TODO エラーで中断した時用にmessagesを保存して再開する仕組みを作る
