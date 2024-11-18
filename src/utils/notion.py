import requests
import json
import os
import datetime
from datetime import timezone, timedelta
from classes.feedback import feedback_to_dict

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DB_ID = os.environ.get("NOTION_DB_ID")

NOTION_API_ENDPOINT = "https://api.notion.com/v1/pages"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def split_text(text, chunk_size=1000):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def save_to_notion(title: str, contents: str) -> requests.Response:
    today = datetime.date.today().isoformat()

    data = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "タイトル": {
                "title": [
                    {
                        "text": {
                            "content": title
                        }
                    }
                ]
            },
            "日付": {

                "date": {
                    "start": today,
                    "end": None
                }
            }
        },
        "children": [
            {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": content
                            }
                        } for content in split_text(contents)
                    ],
                    "language": "json"
                }
            }

        ]
    }

    print("セッション記録をサーバーに送信中です、しばらくお待ちください...")

    response = requests.post(
        NOTION_API_ENDPOINT, headers=HEADERS, data=json.dumps(data))

    if response.status_code == 200:
        print("セッション記録が正常に送信されました")
    else:
        print("セッション記録の送信に失敗しました:", response.status_code, response.text)

    return response


def save_session(messages: list[dict], feedback_message_logs: dict[int, list], params: dict) -> None:
    jst = timezone(timedelta(hours=9))
    formatted_datetime = datetime.datetime.now(jst).strftime("%y%m%d%H%M")
    filename = f"session_{formatted_datetime}"
    file_path = f".log/{filename}.json"

    logs = []
    for i, message in enumerate(messages):
        feedback = feedback_message_logs.get(i, None)
        logs.append(
            {"message": message, "feedback_history": feedback}
        )

    result = {
        "params": params,
        "logs": logs
    }

    output_text = json.dumps(
        result, default=feedback_to_dict, ensure_ascii=False, indent=2)

    with open(file_path, "w") as f:
        f.write(output_text)
        print(f"セッション履歴の保存が完了しました: {file_path}")

    return save_to_notion(filename, output_text)


if __name__ == "__main__":
    save_to_notion("test", "test")
