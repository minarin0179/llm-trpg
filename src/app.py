import os
import json
import streamlit as st
import openai

from utils.diceroll import DICEROOL_TOOL, Dicebot

openai.api_key = os.getenv("OPENAI_API_KEY")

dicebot = Dicebot()

st.set_page_config(page_title="LLM-TRPG", page_icon="🎲")

state = st.session_state

if "messages" not in state:
    state.messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]


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


for message in state.messages:
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
            state.messages.append({
                "role": "tool",
                "content": json.dumps(result),
                "tool_call_id": tool_call["id"]
            })

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

    for message in state.messages:
        print(message, end="\n---\n")

    with st.spinner("GMの返信を待っています..."):
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=state.messages,
            tools=[DICEROOL_TOOL]
        )
        message = response.choices[0].message.to_dict()
        state.messages.append(message)
        st.rerun()

# チャット履歴の保存
if st.button("Save"):
    with open("chat_history.json", "w") as f:
        json.dump(state.messages, f)
    st.write("チャット履歴を保存しました")
