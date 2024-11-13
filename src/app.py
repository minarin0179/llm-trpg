import os
import json
import streamlit as st
import openai

from utils.diceroll import DICEROOL_TOOL, Dicebot

# OpenAIのAPIキーを設定
openai.api_key = os.getenv("OPENAI_API_KEY")

dicebot = Dicebot()

# ページの設定
st.set_page_config(page_title="LLM-TRPG", page_icon="🎲")

state = st.session_state

# チャット履歴の初期化
if "messages" not in state:
    state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

# チャット履歴の表示


def show_message(message):
    role = message["role"]
    content = message["content"]
    match role:
        case "user":
            st.write(f"あなた: {content}")
        case "assistant":
            if content:
                st.write(f"GM: {content}")
        case "tool":
            result = json.loads(content)
            print(f"{result=}")
            if result["ok"]:
                st.write(f"ダイス: {result['text']}")
            else:
                st.error(f"ダイスロールの実行に失敗しました")


for message in state.messages:
    show_message(message)


# Tool Callの処理
submit_tool_call = False
if tool_calls := state.messages[-1].get("tool_calls", None):

    st.write("GM: 以下の内容でダイスロールを実行してよろしいですか？")
    for tool_call in tool_calls:
        command = json.loads(tool_call["function"]["arguments"]).get("command")
        st.write(f"- {command}")

    submit_tool_call = st.button("OK")
    if submit_tool_call:
        for tool_call in tool_calls:
            command = json.loads(
                tool_call["function"]["arguments"]).get("command")
            result = dicebot.exec(command)
            state.messages.append({
                "role": "tool",
                "content": json.dumps(result),
                "tool_call_id": tool_call["id"]
            })

# 入力欄の描画
st.write("---")

with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([7, 1])

    with col1:
        text_input = st.text_input(
            label="あなた",
            key="user_input",
            placeholder="メッセージを入力",
            label_visibility="collapsed"
        )
    with col2:
        submitted = st.form_submit_button("送信")

# 送信時の処理
if submitted or submit_tool_call:
    with st.spinner("AI is thinking..."):
        if state.user_input:
            # 直前のメッセージのtool_callを削除
            if state.messages[-1]["content"]:
                state.messages[-1]["tool_calls"] = None
            else:
                state.messages.pop()

            state.messages.append(
                {"role": "user", "content": state.user_input})

        for message in state.messages:
            print(message, end="\n---\n")

        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=state.messages,
            tools=[DICEROOL_TOOL]
        )

        state.messages.append(response.choices[0].message.to_dict())
        st.rerun()  # 結果を反映して再度描画
