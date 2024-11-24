import requests
import json
import os
import datetime
from datetime import timezone, timedelta
from classes.feedback import feedback_to_dict

NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DB_ID = os.environ.get("NOTION_DB_ID")

NOTION_API_ENDPOINT = "https://api.notion.com/v1/"

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def split_text(text, chunk_size=1000):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]


def create_page(title: str) -> requests.Response:
    today = datetime.date.today().isoformat()

    url = f"{NOTION_API_ENDPOINT}pages"
    data = {
        "parent": {"database_id": NOTION_DB_ID},
        "properties": {
            "タイトル": {
                "title": [{"text": {"content": title}}]
            },
            "日付": {

                "date": {
                    "start": today,
                    "end": None
                }
            }
        }
    }

    response = requests.post(url, headers=HEADERS, data=json.dumps(data))

    return response


def add_blocks(page_id: str, contents: str) -> requests.Response:
    url = f"{NOTION_API_ENDPOINT}blocks/{page_id}/children"

    contents = split_text(contents)

    stride = 10
    for i in range(0, len(contents), stride):
        chunk = contents[i:i+stride]
        payload = {"children": chunk}
        response = requests.patch(
            url, headers=HEADERS, data=json.dumps(payload))

    return response


def save_to_notion(title: str, contents: str) -> requests.Response:
    print("セッション記録をサーバーに送信中です、しばらくお待ちください...")
    page = create_page(title)
    page_id = page.json()["id"]
    if page.status_code != 200:
        print("ページの作成に失敗しました:", page.status_code, page.text)
        return
    print("ページが正常に作成されました")

    children = {
        "children": [
            {
                "object": "block",
                "type": "code",
                "code": {
                    "rich_text": [
                        {
                            "type": "text",
                            "text": {
                                "content": contents
                            }
                        }
                    ],
                    "language": "json"
                }
            }

        ]
    }

    add_blocks(page_id, contents)

    response = requests.post(
        NOTION_API_ENDPOINT, headers=HEADERS, data=json.dumps(data))

    if response.status_code == 200:
        print(f"セッション記録が正常に送信されました ({i + 1}/{len(chunks)})")
    else:
        print("セッション記録の送信に失敗しました:", response.status_code, response.text)

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
