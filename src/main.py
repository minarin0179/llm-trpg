import json
import sys
from openai import OpenAI
from dotenv import load_dotenv
from utils.diceroll import DICEROOL_TOOL, Dicebot, show_diceroll_result
from utils.file import read_text_file
from utils.io import user_input
from utils.ansi import GRAY, RESET
from utils.logger import Logger
from openai.types.chat.chat_completion import ChatCompletion
from datetime import datetime, timezone, timedelta

load_dotenv()
client = OpenAI()

sys.stdout = Logger(".log/recent_output.log")

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
「了解しました」などといった要求に対する応答は必要ありません．
また出力にmarkdown記法を用いてはいけません．
{scenario_text}
{character_text}
{shared_prompt}
"""

assistants = [
    """
    あなたはTRPGのゲームマスターの補佐役です.
    ゲームマスターである私のプレイヤーに対する応答について参照するべきルールがあればそれを引用して補足してください．
    また，私の応答が該当の則っていない場合は，修正方法を提案してください．
    修正すべき点がなければ出力の最後に"OK"，修正するべき点があれば"NG"と返してください.
    ルールブックの内容は以下の通りです．
    {rulebook_text}
    """,
]

messages = [
    {"role": "system", "content": GM_instruction},
    {"role": "user", "content": "それではセッションを始めましょう.まずはシナリオ概要の説明と導入をお願いします."},
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
    temporal_messages_for_gamemaster = messages.copy()

    # feedback loop
    for i in range(MAX_FEEDBACK):
        print(temporal_messages_for_gamemaster)
        temporal_response = client.chat.completions.create(
            model="gpt-4o",
            messages=temporal_messages_for_gamemaster,
            tools=tools,
        )
        debug_print(temporal_response.choices[0].message.content)

        if temporal_response.choices[0].message.content is None:
            # toolcallでcontentがnullの時はダイスを振って追加で応答を生成
            messages.append(temporal_response.choices[0].message.to_dict())
            handle_tool_call(temporal_response)
            return generate_debate_response()

        # contentがnullじゃないときはtoolcallを外す
        temporal_message = temporal_response.choices[0].message.to_dict()
        temporal_message.pop("tool_calls", None)
        temporal_messages_for_gamemaster.append(temporal_message)

        feedbacks = []
        for assistant in assistants:
            temporal_messages = [
                {"role": "system", "content": assistant},
                {"role": "user", "content": f"以下は直近のGMとプレイヤーのやり取りです{
                    # messages[-2:]とtemporalresponseを結合してstringfyする
                    stringfy_messages(temporal_messages_for_gamemaster[-2*(i+1)-1:])}"
                 },
            ]

            print(temporal_messages)
            feedback_response = client.chat.completions.create(
                model="gpt-4o",
                messages=temporal_messages,
                # tools=tools, # feedbackの時はtoolcallを使わない
            )

            debug_print(f"feedback{i} : {
                        feedback_response.choices[0].message.content}")
            # TODO: reasoningも含めて出力
            if feedback_response.choices[0].message.content.endswith("OK"):
                # TODO : 出力制御が上手くいってない jsonモードを試す
                continue

            feedbacks.append(feedback_response)

        if not feedbacks:  # 全員がOKを出したら終了
            final_response = temporal_response
            break
        # feedbackを踏まえてtemporalresponseを更新する
        temporal_messages_for_gamemaster.append(
            {
                "role": "user",
                "content": f"""
                前回の応答に対してフィードバックを与えるので，それらを踏まえて応答をやり直してください．
                「再度やり直します」などの断りは不要です．
                {"\n".join([
                    f"feedback{i} : {feedback.choices[0].message}" for i, feedback in enumerate(feedbacks)
                ])}
                """}
        )
    else:  # 回数上限に達した場合は最終応答を生成
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=temporal_messages_for_gamemaster,
            tools=tools,
        )

    messages.append(final_response.choices[0].message.to_dict())

    print(f"GM : {final_response.choices[0].message.content}")
    print("-"*30)
    return final_response


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


def save_session():
    jst = timezone(timedelta(hours=9))

    # 現在の日時をJSTで取得し、フォーマット
    formatted_datetime = datetime.now(jst).strftime("%y%m%d%H%M")
    file_path = f".log/session_{formatted_datetime}.json"

    with open(file_path, "w") as f:
        json.dump(messages, f, indent=4, ensure_ascii=False)

    # 保存先のパスを表示
    print(f"セッション履歴が保存されました: {file_path}")


def handle_tool_call(response):
    message = response.choices[0].message
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
    return response


if __name__ == "__main__":
    # initial response
    response = generate_response()

    while True:
        user_input_text = user_input()
        if user_input_text == "exit":
            # messagesを「session_日付.json」に保存」
            save_session()
            break
        messages.append({"role": "user", "content": user_input_text})
        # response = generate_response()
        response = generate_debate_response()

        handle_tool_call(response)
    # TODO エラーで中断した時用にmessagesを保存して再開する仕組みを作る
