import json


def convert_character_to_markdown(data):
    # キャラクターの基本情報を取得
    name = data["data"]["name"]
    memo = data["data"]["memo"]

    memo_md = "\n".join([f"- {line}" for line in memo.strip().split("\n")])

    # 能力値を取得
    params = data["data"]["params"]
    params_md = "\n".join(
        [f"- **{param['label']}**: {param['value']}" for param in params])

    # パラメータを取得
    status = data["data"]["status"]
    status_md = "\n".join(
        [f"- **{stat['label']}**: {stat['value']} / {stat['max']}" for stat in status])

    # コマンドを取得
    commands = data["data"]["commands"]
    commands_md = commands.replace("\n", "\n- ")

    # Markdownに変換
    markdown = f"""# キャラクターシート: {name}

**基本情報**
{memo_md}

**メモ**

**能力値**
{params_md}

**パラメータ**
{status_md}

**使用可能なコマンド**
- {commands_md}
"""

    return markdown


json_data = input("CCFOLIA形式でコピーしてペーストしてください: ")
# JSONをPythonオブジェクトに変換し、Markdown生成
character_data = json.loads(json_data)
markdown_output = convert_character_to_markdown(character_data)


# ファイルに保存
file_path = f"character/{character_data['data']['name']}.txt"

with open(file_path, "w") as f:
    f.write(markdown_output)
    print(f"キャラクターシートの保存が完了しました: {file_path}")
