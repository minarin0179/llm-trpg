import requests
import os

NOTION_API_URL_PAGE = "https://api.notion.com/v1/pages"
NOTION_API_URL_CHILDREN = "https://api.notion.com/v1/pages/{page_id}/children"
NOTION_API_KEY = os.environ.get("NOTION_API_KEY")
NOTION_DB_ID = os.environ.get("NOTION_DB_ID")

HEADERS = {
    "Authorization": f"Bearer {NOTION_API_KEY}",
    "Content-Type": "application/json",
    "Notion-Version": "2022-06-28"
}


def split_content(content, max_length=1900):
    """コンテンツを分割する"""
    return [content[i:i + max_length] for i in range(0, len(content), max_length)]


def create_code_block(content):
    """コードブロックを作成"""
    return {
        "object": "block",
        "type": "code",
        "code": {
            "rich_text": [
                {
                    "type": "text",
                    "text": {
                        "content": content
                    }
                }
            ],
            "language": "json"
        }
    }


def create_new_page(database_id, title="New Page"):
    """新しいページを作成"""
    url = NOTION_API_URL_PAGE
    data = {
        "parent": {"database_id": database_id},
        "properties": {
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": title
                    }
                }
            ]
        }
    }
    response = requests.post(url, headers=HEADERS, json=data)
    response_data = response.json()
    if response.status_code != 200:
        raise Exception(f"Failed to create page: {response_data}")
    return response_data["id"]


def send_children(page_id, children):
    """子ブロックを送信"""
    url = NOTION_API_URL_CHILDREN.format(page_id=page_id)
    data = {"children": children}
    response = requests.patch(url, headers=HEADERS, json=data)
    return response.json()


def main(content):
    """メインロジック"""
    # 新しいページを作成
    page_id = create_new_page(NOTION_DB_ID, title="Code Content Page")

    # コンテンツを分割して送信
    chunks = split_content(content)
    for chunk in chunks:
        block = create_code_block(chunk)
        response = send_children(page_id, [block])
        print(response)


if __name__ == "__main__":
    contents = '{"key": "value", "data": ["item1", "item2"]}' * 500  # 大量データ
    main(contents)
