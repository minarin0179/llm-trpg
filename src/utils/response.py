import asyncio

from openai import OpenAI, AsyncOpenAI
from openai.types.chat.chat_completion import ChatCompletion
from datetime import datetime
from classes.assistant import Assistant
from classes.feedback import Feedback, FeedbackWithLog
from utils.diceroll import DICEROOL_TOOL

client = OpenAI()


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


async def generate_multiple_feedbacks(assistans: list[Assistant]) -> list[FeedbackWithLog]:

    async_client = AsyncOpenAI()
    feedback_responses = await asyncio.gather(
        *[
            async_client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=assistant.history,
                response_format=Feedback
            ) for assistant in assistans
        ]
    )

    feedbacks = [
        FeedbackWithLog(
            comment=response.choices[0].message.parsed.comment,
            result=response.choices[0].message.parsed.result,
            created=datetime.fromtimestamp(response.created).isoformat(),
            usage=response.usage.to_dict()
        )
        for response in feedback_responses
    ]

    return feedbacks


# messagesとassistantsのhistoryは内部で更新される
def generate_response(
    messages: list[dict],
    assistants: list[Assistant],
    max_feedback: int,
    feedback_message_logs: dict[int, list] = {}
) -> ChatCompletion:

    current_message_index = len(messages)
    feedback_message_logs[current_message_index] = [
        {
            "user_input_timestamp": datetime.now()
            .replace(microsecond=0).isoformat()}
    ]

    temporal_messages_for_gamemaster = messages.copy()
    tools = [
        DICEROOL_TOOL
    ]

    for assistant in assistants:
        assistant.init_history()
        assistant.add_message(
            {
                "role": "user",
                "content": f"以下は直近のゲームマスターとプレイヤーのやり取りです\n{stringfy_messages(messages[-2:])}"
            }
        )

    # feedback loop
    for i in range(max_feedback):
        temporal_response = client.chat.completions.create(
            model="gpt-4o",
            messages=temporal_messages_for_gamemaster,
            tools=tools,
        )

        if temporal_response.choices[0].message.content is None:
            # toolcallでcontentがnullの時はダイスを振って追加で応答を生成
            messages.append(temporal_response.choices[0].message.to_dict())
            return

        # contentがnullじゃないときはtoolcallを外す
        temporal_message = temporal_response.choices[0].message.to_dict()
        temporal_message["tool_calls"] = None
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
            print(
                f"feedback{i}-{j} : {'OK' if feedback.result else 'NG'}\n{feedback.comment}\n")
            assistants[j].add_message(
                {
                    "role": "assistant",
                    "content": feedback.comment,
                }
            )

        # フィードバックの記録
        if current_message_index not in feedback_message_logs:
            feedback_message_logs[current_message_index] = []

        feedback_message_logs[current_message_index].append(
            {
                "temporal_response": temporal_response.choices[0].message.content,
                "created": datetime.fromtimestamp(temporal_response.created).isoformat(),
                "usage": temporal_response.usage.to_dict(),
                "feedbacks": feedbacks
            })

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

        feedback_message_logs[current_message_index].append(
            {
                "temporal_response": final_response.choices[0].message.content,
                "created": datetime.fromtimestamp(final_response.created).isoformat(),
                "usage": final_response.usage.to_dict(),
            })

    messages.append(final_response.choices[0].message.to_dict())

    print(f"GM : {final_response.choices[0].message.content}")
