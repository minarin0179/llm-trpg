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


def create_long_code_block(page_id, code_string, language='python'):
    """
    非常に長いコードブロックを1つのブロックとしてNotionページに追加します。

    Args:
        token (str): Notion統合のシークレットトークン。
        page_id (str): コードブロックを追加するページのID。
        code_string (str): 追加するコード全体の文字列。
        language (str): コードの言語（デフォルトは'python'）。
    """

    # テキストを適切なサイズに分割（例：1,000文字ごと）
    max_text_size = 1000  # 1つのリッチテキストオブジェクトの最大文字数
    code_chunks = [code_string[i:i+max_text_size]
                   for i in range(0, len(code_string), max_text_size)]

    # リッチテキストオブジェクトのリストを作成
    rich_text_objects = []
    for chunk in code_chunks:
        rich_text = {
            "type": "text",
            "text": {
                "content": chunk
            }
        }
        rich_text_objects.append(rich_text)

    # コードブロックを作成
    code_block = {
        "object": "block",
        "type": "code",
        "code": {
            "text": rich_text_objects,
            "language": language
        }
    }

    # ページにブロックを追加
    url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    payload = {
        "children": [code_block]
    }

    response = requests.patch(url, headers=HEADERS, json=payload)

    return response


def add_text_to_code_block(page_id: str, block_id: str, text: str) -> requests.Response:
    url = f"{NOTION_API_ENDPOINT}blocks/{block_id}/children"
    data = {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": text
                    }
                }
            ],
            "language": "json"
        }
    }

    response = requests.patch(url, headers=HEADERS, data=json.dumps(data))

    return response


def save_to_notion(title: str, contents: str) -> requests.Response:

    page = create_page(title)
    page_id = page.json()["id"]

    response = create_long_code_block(page_id, contents, language='json')

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
