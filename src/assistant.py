from openai import OpenAI
from dotenv import load_dotenv
from typing_extensions import override
from openai import AssistantEventHandler

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

shared_prompt = f"""
回答は常に日本語でお願いします．
"""

GM_instruction = f"""
あなたはTRPGのゲームマスターです.
今から{system}のシナリオを一緒に遊びましょう．
あなたの他にも複数のGMが居るので彼らと相談しながら，
GM達の意見を取りまとめてあなたが総意をプレイヤーに伝えてください．
{scenario_text}
{character_text}
{shared_prompt}
"""

tools = [
    {
        "type": "function",
        "function": {
            "name": "diceroll",
            "description": "Execute a die roll. BCDice is used for die rolls. If a die roll is requested, find the appropriate die roll in the chat palette and output it as a command. If there is no command in the chat palette and a command is explicitly given, execute it. If none of the above apply, there is no need to execute the command.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Command that can be executable in Bcdice. ",
                    }
                },
                "required": ["command"],
            },
        },
    }
]

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


# async
class EventHandler(AssistantEventHandler):
    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)

    @override
    def on_event(self, event):
        # Retrieve events that are denoted with 'requires_action'
        # since these will have our tool_calls
        if event.event == "thread.run.requires_action":
            print("action!")
            run_id = event.data.id  # Retrieve the run ID from the event data
            self.handle_requires_action(event.data, run_id)

    def handle_requires_action(self, data, run_id):
        tool_outputs = []

        for tool in data.required_action.submit_tool_outputs.tool_calls:
            if tool.function.name == "diceroll":
                tool_outputs.append({"tool_call_id": tool.id, "output": "6"})

        # Submit all tool_outputs at the same time
        self.submit_tool_outputs(tool_outputs, run_id)

    def submit_tool_outputs(self, tool_outputs, run_id):
        client.beta.threads.runs.submit_tool_outputs(
            thread_id=self.current_run.thread_id,
            run_id=run_id,
            tool_outputs=tool_outputs,
        )

        # Use the submit_tool_outputs_stream helper
        # with client.beta.threads.runs.submit_tool_outputs_stream(
        #     thread_id=self.current_run.thread_id,
        #     run_id=self.current_run.id,
        #     tool_outputs=tool_outputs,
        #     event_handler=EventHandler(),
        # ) as stream:
        #     for text in stream.text_deltas:
        #         print(text, end="", flush=True)
        #     print()

while True:
    with client.beta.threads.runs.stream(
        thread_id=thread.id,
        assistant_id=GM.id,
        event_handler=EventHandler(),
    ) as stream:
        stream.until_done()

    user_input = input("\n> ")

    if user_input == "exit":
        break

    message = client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input,
    )
