import os
import json
import streamlit as st
import openai
from prompts import init_messages, load_assistants
from utils.diceroll import DICEROOL_TOOL, Dicebot
from utils.notion import save_session
from utils.response import generate_response


openai.api_key = os.getenv("OPENAI_API_KEY")

dicebot = Dicebot("Emoklore")


assistants = load_assistants()

# streamlitの設定
st.set_page_config(page_title="LLM-TRPG", page_icon="🎲")
state = st.session_state

if "feedback_message_logs" not in state:
    state.feedback_message_logs = {}

if "messages" not in state:
    state.messages = init_messages()
    # state.messages = [
    #     {"role": "system", "content": "you are a helpful assistant"}]

    generate_response(
        messages=state.messages,
        assistants=assistants,
        max_feedback=0,
        feedback_message_logs=state.feedback_message_logs
    )


def show_message(message):
    role = message["role"]
    content = message["content"]
    if not content:
        return
    match role:
        case "user":
            st.chat_message("user").write(content)
        case "assistant":
            st.chat_message("assistant").write(content)
        case "tool":
            result = json.loads(content)
            if result["ok"]:
                st.chat_message("🎲").write(result['text'])
            else:
                st.error(f"ダイスロールの実行に失敗しました")


# チャット履歴の表示
for message in state.messages[len(init_messages()):]:
    show_message(message)


# Tool Callの処理
submit_tool_call = False
if tool_calls := state.messages[-1].get("tool_calls", None):
    commands = [
        json.loads(tool_call["function"]["arguments"]).get("command")
        for tool_call in tool_calls
    ]
    with st.chat_message("assistant"):
        st.write("以下の内容でダイスロールを実行してよろしいですか？")
        for command in commands:
            st.write(f"- {command}")

    if submit_tool_call := st.button("OK"):
        for tool_call, command in zip(tool_calls, commands):
            result = dicebot.exec(command)
            message = {
                "role": "tool",
                "content": json.dumps(result),
                "tool_call_id": tool_call["id"]
            }
            state.messages.append(message)
            show_message(message)

user_input = st.chat_input("メッセージを送信")

# 送信時の処理
if user_input or submit_tool_call:

    if user_input:
        # 直前のメッセージのtool_callを削除
        if state.messages[-1]["content"]:
            state.messages[-1]["tool_calls"] = None
        else:
            state.messages.pop()

        state.messages.append(
            {"role": "user", "content": user_input})

        show_message({"role": "user", "content": user_input})
        user_input.update(disabled=True)

    for message in state.messages:
        print(message, end="\n---\n")

    with st.spinner("GMの返信を待っています..."):
        # response = openai.chat.completions.create(
        #     model="gpt-4o",
        #     messages=state.messages,
        #     tools=[DICEROOL_TOOL]
        # )

        # message = response.choices[0].message.to_dict()
        # state.messages.append(message)
        generate_response(
            messages=state.messages,
            assistants=assistants,
            max_feedback=3,
            feedback_message_logs=state.feedback_message_logs
        )
        st.rerun()

# サイドバー
with st.sidebar:
    # チャット履歴の保存
    if st.button("履歴をサーバーに保存"):
        msg = st.toast("セッション記録をサーバーに送信しています...", icon="ℹ️")
        response = save_session(
            state.messages, state.feedback_message_logs)

        if response.status_code == 200:
            msg.toast("セッション記録が正常に送信されました", icon="✅")
        else:
            msg.toast("セッション記録の送信に失敗しました", icon="❌")

    # フィードバックの表示
    st.toggle("フィードバックを表示", value=False, key="show_feedback")
