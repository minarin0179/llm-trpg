import os 
from autogen import ConversableAgent, GroupChatManager, GroupChat
from dotenv import load_dotenv
load_dotenv()


group_chat_with_introductions = GroupChat(
    agents=[adder_agent, multiplier_agent, subtracter_agent, divider_agent, number_agent],
    messages=[],
    max_round=6,
    send_introductions=True,
)

group_chat_manager_with_intros = GroupChatManager(
    groupchat=group_chat_with_introductions,
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
)

arithmetic_agent = ConversableAgent(
    name="Arithmetic_Agent",
    llm_config=False,
    human_input_mode="ALWAYS",
    # This agent will always require human input to make sure the code is
    # safe to execute.
    code_execution_config={"use_docker": False, "work_dir": temp_dir},
)

code_writer_agent = ConversableAgent(
    name="Code_Writer_Agent",
    system_message="You are a code writer. You write Python script in Markdown code blocks.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)

poetry_agent = ConversableAgent(
    name="Poetry_Agent",
    system_message="You are an AI poet.",
    llm_config={"config_list": [{"model": "gpt-4", "api_key": os.environ["OPENAI_API_KEY"]}]},
    human_input_mode="NEVER",
)

nested_chats = [
    {
        "recipient": group_chat_manager_with_intros,
        "summary_method": "reflection_with_llm",
        "summary_prompt": "Summarize the sequence of operations used to turn " "the source number into target number.",
    },
    {
        "recipient": code_writer_agent,
        "message": "Write a Python script to verify the arithmetic operations is correct.",
        "summary_method": "reflection_with_llm",
    },
    {
        "recipient": poetry_agent,
        "message": "Write a poem about it.",
        "max_turns": 1,
        "summary_method": "last_msg",
    },
]

arithmetic_agent.register_nested_chats(
    nested_chats,
    trigger=lambda sender: sender not in [group_chat_manager_with_intros, code_writer_agent, poetry_agent],
)

reply = arithmetic_agent.generate_reply(
    messages=[{"role": "user", "content": "I have a number 3 and I want to turn it into 7."}]
)