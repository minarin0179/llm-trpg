import json
import sys
import os
from openai import OpenAI
from dotenv import load_dotenv
from utils.diceroll import DICEROOL_TOOL, Dicebot, show_diceroll_result
from utils.file import read_text_file
from utils.io import user_input
from utils.ansi import GRAY, RESET
from utils.logger import Logger
from utils.notion import save_to_notion
from openai.types.chat.chat_completion import ChatCompletion
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel


load_dotenv()
client = OpenAI()

sys.stdout = Logger(".log/recent_output.log")

GAME_SYSTEM = "エモクロアTPRG"

dicebot = Dicebot("Emoklore")

MAX_FEEDBACK = 3
DEBUG = os.getenv("ENV", "production") == "development"

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
    ゲームマスターである私のプレイヤーに対する応答について参照するべきルールがあればそれを引用してcommentで補足してください.
    また，私の応答が該当の則っていない場合はcommentで修正方法を提案してください.
    commentは日本語でお願いします．
    修正すべき点がなければresultにTrue，修正するべき点があればresultにFalseを返してください.
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
    if DEBUG and text:
        print(f"{GRAY}{text}{RESET}")


class Feedback(BaseModel):
    comment: str
    result: bool


def generate_debate_response() -> ChatCompletion:

    print("GM: 考え中...", end="\r")
    temporal_messages_for_gamemaster = messages.copy()

    # feedback loop
    for i in range(MAX_FEEDBACK):
        temporal_response = client.chat.completions.create(
            model="gpt-4o",
            messages=temporal_messages_for_gamemaster,
            tools=tools,
        )
        debug_print(temporal_response.choices[0].message.content)

        if temporal_response.choices[0].message.content is None:
            # toolcallでcontentがnullの時はダイスを振って追加で応答を生成
            messages.append(temporal_response.choices[0].message.to_dict())
            return handle_tool_call(temporal_response)

        # contentがnullじゃないときはtoolcallを外す
        temporal_message = temporal_response.choices[0].message.to_dict()
        temporal_message.pop("tool_calls", None)
        temporal_messages_for_gamemaster.append(temporal_message)

        feedbacks: list[Feedback] = []
        for assistant in assistants:
            temporal_messages = [
                {"role": "system", "content": assistant},
                {"role": "user", "content": f"以下は直近のGMとプレイヤーのやり取りです{
                    # messages[-2:]とtemporalresponseを結合してstringfyする
                    stringfy_messages(temporal_messages_for_gamemaster[-2*(i+1)-1:])}"
                 },
            ]

            feedback_response = client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=temporal_messages,
                response_format=Feedback
            )

            feedback = feedback_response.choices[0].message.parsed

            debug_print(f"feedback{i} : {"OK" if feedback.result else "NG"}\n{
                        feedback.comment}\n")
            if feedback.result:
                continue

            feedbacks.append(feedback)

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
                    f"feedback{i} : {feedback.comment}" for i, feedback in enumerate(feedbacks)
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
    handle_tool_call(final_response)
    return final_response


def generate_response(temporal: bool = False) -> ChatCompletion:

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
    )

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
    formatted_datetime = datetime.now(jst).strftime("%y%m%d%H%M")
    filename = f"session_{formatted_datetime}"
    file_path = f".log/{filename}.json"

    with open(file_path, "w") as f:
        json.dump(messages, f, indent=4, ensure_ascii=False)
        print(f"セッション履歴の保存が完了しました: {file_path}")

    save_to_notion(filename, json.dumps(
        messages, indent=4, ensure_ascii=False))


def handle_tool_call(response: ChatCompletion) -> None:
    message = response.choices[0].message
    tool_call = message.tool_calls[0] if message.tool_calls else None

    # toolcallがない場合は何もしない
    if not tool_call or tool_call.function.name != "diceroll":
        return

    arguments = json.loads(tool_call.function.arguments)
    command = arguments.get("command")

    print(f"""GM: 「{command}」でダイスロールを実行して良いですか？
(問題なければ何も入力せずEnterを押してください)
""")
    user_input_text = input("> ")

    if user_input_text == "":

        diceroll_result = dicebot.exec(command)
        show_diceroll_result(diceroll_result)
        print("-"*30)

        func_result = {
            "role": "tool",
            "content": json.dumps(diceroll_result),
            "tool_call_id": response.choices[0].message.tool_calls[0].id,
        }

        messages.append(func_result)
        generate_debate_response()
    else:
        last_message = messages.pop()
        if last_message.get("content", None):
            # contentがある場合はtoolcallを消して戻す
            last_message.pop("tool_calls", None)
            messages.append(last_message)
        messages.append({"role": "user", "content": user_input_text})
        generate_debate_response()


if __name__ == "__main__":
    try:
        response = generate_response()

        while True:
            user_input_text = user_input()
            if user_input_text == "exit":
                save_session()
                break
            messages.append({"role": "user", "content": user_input_text})
            print("-"*30)
            # response = generate_response() # single agent
            generate_debate_response()

    except Exception as e:
        print(e)
        save_session()
        raise e
