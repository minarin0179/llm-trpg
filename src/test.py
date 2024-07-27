

config_list = [
    {
        "model": "gpt-4o",
        "api_key": "API Key",
    }
]


llm_config = {
    "functions": [
        {
            "name": "answer_question",
            "description": "論文の内容に関する質問に答えることができます。",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "論文の内容に関する質問",
                    }
                },
                "required": ["question"],
            },
        },
    ],
    "config_list": config_list,
    "timeout": 120,
}