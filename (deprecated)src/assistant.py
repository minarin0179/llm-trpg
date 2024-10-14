import json
from openai import OpenAI
from dotenv import load_dotenv
from typing_extensions import override
from openai import AssistantEventHandler
from diceroll import diceroll

load_dotenv()
client = OpenAI()

system = "エモクロアTPRG"


SCENARIO_PATH = "scenario/hasshakusama_scenario.txt"
scenario_text = "シナリオの内容は以下の通りです．\n"
with open(SCENARIO_PATH, "r", encoding="utf-8") as file:
    scenario_text += file.read()

CHARACTER_PATH = "character/hibiki.txt"

character_text = "プレイヤーのキャラクターの情報は以下の通りです.\n"
with open(CHARACTER_PATH, "r", encoding="utf-8") as file:
    character_text += file.read()

RULEBOOK_PATH = "rulebook/emoklore.txt"
rulebook_text = "ルールブックの内容は以下の通りです.\n"
with open(RULEBOOK_PATH, "r", encoding="utf-8") as file:
    rulebook_text += file.read()


# GM_instruction = """
# You are an excellent TPRG game master. I will tell you the rules and scenarios to use and we will start the session together! Conversations will be conducted in Japanese.
# Do not give too much advice or hints in order to encourage positive action from the player.
# Keep the session on track with the scenario, and if things get too far off-topic, let the conversation naturally pick up where it left off.
# You know all the details of the scenario, but players do not know the scenario, so use your best efforts not to spoil it for them.
# Reveal core information about the scenario gradually during the session.
# You do not need to explain the rules unless asked to do so.
# Please do your best to avoid making up content that is not included in the scenario.
# When speaking to me as an NPC, please end the conversation with the NPC's lines so that I can respond as a character.
# """
tools = [
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "diceroll",
    #         "description": """Execute a die roll.
    #         BCDice is used for die rolls.
    #         If a die roll is requested, find the appropriate die roll in the chat palette and output it as a command.
    #         If there is no command in the chat palette and a command is explicitly given, execute it.
    #         Variables enclosed in {} should be filled in by referring to the required value from the dialogue history.
    #         If none of the above apply, there is no need to execute the command.""",
    #         "parameters": {
    #             "type": "object",
    #             "properties": {
    #                 "command": {
    #                     "type": "string",
    #                     "description": "Command that can be executable in Bcdice. ",
    #                 }
    #             },
    #             "required": ["command"],
    #         },
    #     },
    # }
    {
        "type": "function",
        "function": {
            "name": "diceroll",
            "description": """This function executes a dice roll using the BCDice system.
The function processes die roll requests based on chat palette commands or explicit input from the user. 
- If the die roll can be found in the chat palette, extract and execute the relevant command.
- If no command is available in the chat palette and the user provides an explicit roll command, execute it as given.
- If the die roll requires a variable (e.g., a character's stat or modifier) enclosed in curly braces {}, refer to the dialogue history to retrieve and fill in the necessary value.
- If none of the above conditions are met, the die roll does not need to be executed.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The dice roll command that can be executed using BCDice."
                    }
                },
                "required": ["command"]
            }
        }
    }
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


GM = client.beta.assistants.create(
    name="GameMaster",
    instructions=GM_instruction,
    tools=tools,
    model="gpt-4o",
)

thread = client.beta.threads.create()

message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="セッションを始めましょう",
)


# def ask_to_rule(thread_id):
#     # スレッドを取得
#     original_messages = client.beta.threads.messages.list(thread_id=thread_id)

#     messages = [
#         {
#             "role": message.role,
#             "content": message.content[0].text.value,
#         }
#         for message in original_messages
#     ]

#     # 新しいスレッドを作成して履歴をコピー
#     new_thread = client.beta.threads.create(
#         messages=messages,
#     )

#     rule_instruction = f"""
#     あなたはTRPGのゲームマスターです.
#     私の入力した行動の内容に対して，該当するルールや判定方法の詳細について教えてください
#     ルールブックの内容は以下の通りです．
#     {rulebook_text}
#     """

#     rule_assistant = client.beta.assistants.create(
#         name="RuleAssistant",
#         instructions=rule_instruction,
#         tools=tools,
#         model="gpt-4o",
#     )

#     run = client.beta.threads.runs.create_and_poll(
#         thread_id=new_thread.id,
#         assistant_id=rule_assistant.id,
#         instructions="ルールについて教えてください",
#     )
#     if run.status == "completed":
#         print("completed")
#         messages = client.beta.threads.messages.list(thread_id=thread.id)
#         print(messages)
#     else:
#         print("uncompleted")
#         print(run.status)


def ask_to_rule(history):
    rule_instruction = f"""
    あなたはTRPGのゲームマスターです.
    私の入力した行動の内容に対して，該当するルールや判定方法の詳細について教えてください
    ただし，ロールプレイや描写などのルールに関係ない会話の場合は"None"とだけ返信してください
    ルールブックの内容は以下の通りです．
    {rulebook_text}
    """

    messages = [
        {"role": "system", "content": rule_instruction},
        *history,
    ]

    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    result = completion.choices[0].message.content
    if result == "None":
        return None

    print("\033[31m" + result + "\033[0m")
    return result


function_skip_message = None


def get_history(thread_id):
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    return [{
        "role": message.role,
        "content": message.content[0].text.value,
    } for message in messages][::-1]


def switch_role(history):
    new_history = history.copy()
    for message in new_history:
        if message["role"] == "user":
            message["role"] = "system"
        elif message["role"] == "system":
            message["role"] = "user"

    return new_history


class EventHandler(AssistantEventHandler):
    @override
    def on_event(self, event):
        # Retrieve events that are denoted with 'requires_action'
        # since these will have our tool_calls
        if event.event == "thread.run.requires_action":
            run_id = event.data.id  # Retrieve the run ID from the event data
            self.handle_requires_action(event.data, run_id)

    def handle_requires_action(self, data, run_id):
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            if tool.function.name == "diceroll":
                command = json.loads(tool.function.arguments)["command"]
                print(
                    f"以下の内容でダイスロールを行います．よろしいですか？\n{
                        command}\n(問題なければそのままEnterを押してください)"
                )

                if len(function_skip_message := input()) > 0:
                    return
                result = diceroll(command)
                if not result.get("ok", False):
                    print("ダイスロールの実行中に問題が発生しました.")
                    print(f"{command=}")
                    print(f"{result=}")
                    return
                print(result["text"])
                tool_outputs.append(
                    {"tool_call_id": tool.id, "output": json.dumps(result)}
                )

        # Submit all tool_outputs at the same time
        self.submit_tool_outputs(tool_outputs, run_id)

    def submit_tool_outputs(self, tool_outputs, run_id):
        # Use the submit_tool_outputs_stream helper
        with client.beta.threads.runs.submit_tool_outputs_stream(
            thread_id=self.current_run.thread_id,
            run_id=self.current_run.id,
            tool_outputs=tool_outputs,
            event_handler=EventHandler(),
        ) as stream:
            for text in stream.text_deltas:
                print(text, end="", flush=True)
            print()


while True:
    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=GM.id,
        event_handler=EventHandler(),
    ) as stream:
        # stream.until_done()
        for text in stream.text_deltas:
            print(text, end="", flush=True)
        print()

    if function_skip_message:
        user_input = function_skip_message
        function_skip_message = None
    else:
        while True:
            user_input = input("> ")
            if len(user_input) > 0:
                break

    if user_input == "exit":
        break

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input,
    )

    # メッセージ履歴を表示
    print(get_history(thread.id))

    result = ask_to_rule(get_history(thread.id)[-2:])

    if result is not None:
        print(result)
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=result,
        )


def generate_response(prompt):
    try:
        client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
            ],
        )
    except Exception as e:
        return str(e)
