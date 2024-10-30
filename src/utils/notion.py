import requests
import json
import datetime
import os


NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DB_ID = os.environ.get("NOTION_DB_ID")

NOTION_API_ENDPOINT = "https://api.notion.com/v1/pages"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def split_text(text, chunk_size=1999):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def save_to_notion(title: str, contents: str):
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


if __name__ == "__main__":
    save_to_notion("test", "test")
