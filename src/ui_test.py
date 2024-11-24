import json
import sys
import os
import asyncio
import streamlit as st
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv
from utils.diceroll import DICEROOL_TOOL, Dicebot, show_diceroll_result
from utils.file import read_text_file
from utils.io import user_input
from utils.ansi import GRAY, RESET,  MAGENTA
from utils.logger import Logger
from utils.notion import save_to_notion
from classes.assistant import Assistant
from openai.types.chat.chat_completion import ChatCompletion
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel


load_dotenv()
client = OpenAI()

sys.stdout = Logger(".log/recent_output.log")

GAME_SYSTEM = "エモクロアTPRG"

dicebot = Dicebot("Emoklore", no_check=True)

MAX_FEEDBACK = 3
DEBUG = os.getenv("ENV", "production") == "development"

SCENARIO_PATH = "scenario/hasshakusama_scenario.txt"
scenario_text = f"シナリオの内容は以下の通りです．\n{read_text_file(SCENARIO_PATH)}"

CHARACTER_PATH = "character/意欲的な新米探偵.txt"

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
「了解しました」などといった要求に対する返答を都度行う必要はありません．
また出力にmarkdown記法を用いてはいけません．
ゲームマスターを行うにあたって以下のような点に留意してください．
1. 極力シナリオやルールブックに則ってプレイヤーに対する応答を行ってください．
2. シナリオのネタバレをしないでください．あなたに渡されているシナリオ情報を対話開いてであるプレイヤーは知りません．適切な時が来るまで情報を伏せてください．
3. 一度に多くの情報を伝えるのではなく，プレイヤーの行動に応じて情報を適切に提供してください．
4. シナリオの内容から大きく逸脱しないで下さい．多少のアドリブは許容されますが，シナリオの進行に大きな影響を与えるような行動は避けてください．
{shared_prompt}
{rulebook_text}
{scenario_text}
{character_text}
"""


assistants = [
    Assistant(f"""
あなたはTRPGのゲームマスターの補佐役です.
まずゲームマスターである私のプレイヤーに対する応答について参照するべきルールがあればそれを引用してcommentで補足してください.
そして，私の応答が該当のルールに則っていない場合はcommentで修正方法を提案してください.
commentは日本語でお願いします．
修正すべき点がなければresultにTrue，修正するべき点があればresultにFalseを返してください.
ルールブックの内容は以下の通りです．
{rulebook_text}"""),
    Assistant(f"""
あなたはTRPGのゲームマスターの補佐役です.
まず，ゲームマスターである私のプレイヤーに対する応答についてシナリオに関連する内容があればシナリオの該当部分を引用してcommentで補足してください.
そして，私の応答がシナリオと矛盾していたり，大きく逸脱している場合はcommentで修正方法を提案してください.
commentは日本語でお願いします．
修正すべき点がなければresultにTrue，修正するべき点があればresultにFalseを返してください.
シナリオの内容は以下の通りです．
{scenario_text}"""),
]


def stringfy_messages(messages: list[dict]) -> str:
    role_map = {
        "user": "Player",
        "system": "GM",
        "assistant": "GM",
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

    def to_dict(self):
        return {
            "comment": self.comment,
            "result": self.result
        }


def feedback_to_dict(obj):
    if isinstance(obj, Feedback):
        return obj.to_dict()
    raise


async def generate_multiple_feedbacks(assistans: list[Assistant]):
    client = AsyncOpenAI()

    feedback_responses = await asyncio.gather(
        *[
            client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=assistant.history,
                response_format=Feedback
            ) for assistant in assistans
        ]
    )
    feedback = [
        response.choices[0].message.parsed for response in feedback_responses]

    return feedback


def generate_response(
        messages: list[dict],
        feedback_message_logs: dict[int, list] = {},
        no_debate=False
) -> ChatCompletion:

    print(f"{GRAY}GM: 考え中...{RESET}", end="\r")
    temporal_messages_for_gamemaster = messages.copy()

    for assistant in assistants:
        assistant.init_history()
        assistant.add_message(
            {
                "role": "user",
                "content": f"以下は直近のゲームマスターとプレイヤーのやり取りです\n{stringfy_messages(messages[-2:])}"
            }
        )

    # feedback loop
    for i in range(MAX_FEEDBACK if not no_debate else 0):
        temporal_response = client.chat.completions.create(
            model="gpt-4o",
            messages=temporal_messages_for_gamemaster,
            tools=tools,
        )
        debug_print(temporal_response.choices[0].message.content)

        if temporal_response.choices[0].message.content is None:
            # toolcallでcontentがnullの時はダイスを振って追加で応答を生成
            messages.append(temporal_response.choices[0].message.to_dict())
            return handle_tool_call(temporal_response, messages)

        # contentがnullじゃないときはtoolcallを外す
        temporal_message = temporal_response.choices[0].message.to_dict()
        temporal_message.pop("tool_calls", None)
        temporal_messages_for_gamemaster.append(temporal_message)

        for assistant in assistants:
            assistant.add_message(
                {
                    "role": "user",
                    "content": f"以下はこれに続くGMの応答です「{temporal_message["content"]}」"
                } if i == 0 else {
                    "role": "user",
                    "content": f"フィードバックを元に応答を考え直しました．再度フィードバックを行ってください.「{temporal_message["content"]}」"
                }
            )

        feedbacks = asyncio.run(generate_multiple_feedbacks(assistants))

        for j, feedback in enumerate(feedbacks):
            debug_print(
                f"feedback{i}-{j} : {'OK' if feedback.result else 'NG'}\n{feedback.comment}\n")
            assistants[j].add_message(
                {
                    "role": "assistant",
                    "content": feedback.comment,
                }
            )

        # フィードバックの記録
        current_message_index = len(messages)
        if current_message_index not in feedback_message_logs:
            feedback_message_logs[current_message_index] = []

        feedback_message_logs[current_message_index].append(
            {"temporal_response": temporal_response.choices[0].message.content, "feedbacks": feedbacks})

        NG_feedbacks = [
            feedback for feedback in feedbacks if not feedback.result]

        if not NG_feedbacks:
            final_response = temporal_response
            break

        temporal_messages_for_gamemaster.append(
            {
                "role": "user",
                "content": f"""
前回の応答に対していくつかフィードバックを与えるので，それらを踏まえて応答をやり直してください．
「再度やり直します」などの断りは不要です．以下はフィードバックの内容です.
{"\n".join([f"{i}. : {feedback.comment}" for i,
                    feedback in enumerate(feedbacks)])}
                """}
        )
    else:  # 回数上限に達した場合は最終応答を生成
        final_response = client.chat.completions.create(
            model="gpt-4o",
            messages=temporal_messages_for_gamemaster,
            tools=tools,
        )

    messages.append(final_response.choices[0].message.to_dict())

    print(f"{MAGENTA}GM : {final_response.choices[0].message.content}{RESET}")
    print("-"*30)
    handle_tool_call(final_response, messages)
    st.rerun()
    return final_response


def save_session(messages: list[dict], feedback_message_logs: dict[int, list] = {}):
    jst = timezone(timedelta(hours=9))
    formatted_datetime = datetime.now(jst).strftime("%y%m%d%H%M")
    filename = f"session_{formatted_datetime}"
    file_path = f".log/{filename}.json"

    logs = []
    for i, message in enumerate(messages):
        feedback = feedback_message_logs.get(i, None)
        logs.append(
            {"message": message, "feedback_history": feedback}
        )

    output_text = json.dumps(
        logs, default=feedback_to_dict, ensure_ascii=False, indent=2)

    with open(file_path, "w") as f:
        f.write(output_text)
        print(f"セッション履歴の保存が完了しました: {file_path}")

    save_to_notion(filename, output_text)


def handle_tool_call(response: ChatCompletion, messages: list[dict]) -> None:
    message = response.choices[0].message
    tool_calls = message.tool_calls if message.tool_calls else []
    commands = [json.loads(tool_call.function.arguments).get("command")
                for tool_call in tool_calls]

    # toolcallがない場合は何もしない
    if not tool_calls:
        return

    st.write(f"GM: 以下のダイスロールを実行してよいですか？")
    for command in commands:
        st.write(f"- {command}")

    confirm_button = st.button("OK", key=f"toolcall_confirm_button")
    user_input_text = st.text_input(
        "他に何か指示があれば入力してください", key=f"toolcall_user_input")

    if confirm_button:
        for tool_call in tool_calls:
            arguments = json.loads(tool_call.function.arguments)
            command = arguments.get("command")
            diceroll_result = dicebot.exec(command)
            st.write(diceroll_result)

            func_result = {
                "role": "tool",
                "content": json.dumps(diceroll_result),
                "tool_call_id": tool_call.id,
            }
            messages.append(func_result)
        print(messages)
        generate_response(
            messages, feedback_message_logs=st.session_state.feedback_message_logs)

    if user_input_text:
        last_message = messages.pop()
        if last_message.get("content", None):
            # contentがある場合はtoolcallを消して戻す
            last_message.pop("tool_calls", None)
            messages.append(last_message)
        messages.append({"role": "user", "content": user_input_text})
        generate_response(
            messages, feedback_message_logs=st.session_state.feedback_message_logs)


if __name__ == "__main__":

    if "feedback_message_logs" not in st.session_state:
        st.session_state["feedback_message_logs"] = {}

    if "messages" not in st.session_state:
        st.session_state["messages"] = [
            {"role": "system", "content": GM_instruction},
            {"role": "user", "content": "それではセッションを始めましょう.まずはシナリオ概要の説明と導入をお願いします."},
        ]

        # 最初の応答を生成
        generate_response(st.session_state.messages, no_debate=True,
                          feedback_message_logs=st.session_state.feedback_message_logs)

    for message in st.session_state.messages[2:]:
        role = "あなた" if message["role"] == "user" else "GM"
        st.write(f"{role}: {message['content']}")

    st.write("---")

    with st.form("chat_form", clear_on_submit=True):
        col1, col2 = st.columns(
            [7, 1],
            vertical_alignment="bottom"
        )  # カラムの比率を指定（左:4、右:1）

        with col1:
            user_input = st.text_input(
                "あなた",
                key="user_input",
                placeholder="メッセージを入力",
                label_visibility="collapsed"
            )
        with col2:
            submitted = st.form_submit_button("送信")

    # メッセージ送信ボタン
    if submitted:
        st.write(f"あなた: {st.session_state.user_input}")
        user_input_text = st.session_state.user_input
        if user_input_text == "exit":
            save_session(st.session_state.messages,
                         st.session_state.feedback_message_logs)
            # st.stop()

        st.session_state.messages.append(
            {"role": "user", "content": user_input_text})

        with st.spinner("GM: 考え中..."):
            generate_response(
                st.session_state.messages, feedback_message_logs=st.session_state.feedback_message_logs)

    # while True:
    #     user_input_text = user_input()
    #     if user_input_text == "exit":
    #         save_session(st.session_state.messages, feedback_message_logs)
    #         break
    #     messages.append({"role": "user", "content": user_input_text})
    #     print("-"*30)
    #     generate_response(
    #         messages, feedback_message_logs=feedback_message_logs)
