import streamlit as st
from utils.file import read_text_file
from classes.settings import Settings
from setting import SCENARIO_PATH, CHARACTER_PATH, RULEBOOK_PATH, GAME_SYSTEM
from classes.assistant import Assistant


shared_prompt = f"""
回答は常に日本語でお願いします．
"""


def load_GM_instruction(settings: Settings):

    scenario_text = f"シナリオの内容は以下の通りです．\n{
        read_text_file(settings["scenario_path"])}"
    character_text = f"プレイヤーのキャラクターの情報は以下の通りです.\n{
        read_text_file(settings['character_path'])}"
    rulebook_text = f"ルールブックの内容は以下の通りです.\n{
        read_text_file(settings['rulebook_path'])}"
    return f"""
あなたはTRPGのゲームマスターです.
今から{settings['game_system']}のシナリオを一緒に遊びましょう．
「了解しました」などといった要求に対する返答を都度行う必要はありません．
また出力にmarkdown記法を用いてはいけません．
ゲームマスターを行うにあたって以下のような点に留意してください．
1. 極力シナリオやルールブックに則ってプレイヤーに対する応答を行ってください．
2. シナリオのネタバレをしないでください．あなたに渡されているシナリオ情報を対話開いてであるプレイヤーは知りません．適切な時が来るまで情報を伏せてください．
3. 一度に多くの情報を伝えるのではなく，プレイヤーの行動に応じて情報を適切に提供してください．
4. シナリオの内容から大きく逸脱しないで下さい．多少のアドリブは許容されますが，シナリオの進行に大きな影響を与えるような行動は避けてください．
{shared_prompt}
{rulebook_text}
{scenario_text}
{character_text}
"""


def load_assistants(settings):
    rulebook_text = f"ルールブックの内容は以下の通りです.\n{
        read_text_file(settings["rulebook_path"])}"

    scenario_text = f"シナリオの内容は以下の通りです．\n{
        read_text_file(settings['scenario_path'])}"

    return [
        Assistant(f"""
あなたはTRPGのゲームマスターの補佐役です.
まずゲームマスターである私のプレイヤーに対する応答について参照するべきルールがあればそれを引用してcommentで補足してください.
そして，私の応答が該当のルールに則っていない場合はcommentで修正方法を提案してください.
commentは日本語でお願いします．
修正すべき点がなければresultにTrue，修正するべき点があればresultにFalseを返してください.
ルールブックの内容は以下の通りです．
{rulebook_text}"""
        ),
        Assistant(f"""
あなたはTRPGのゲームマスターの補佐役です.
まず，ゲームマスターである私のプレイヤーに対する応答についてシナリオに関連する内容があればシナリオの該当部分を引用してcommentで補足してください.
そして，私の応答がシナリオと矛盾していたり，大きく逸脱している場合はcommentで修正方法を提案してください.
commentは日本語でお願いします．
修正すべき点がなければresultにTrue，修正するべき点があればresultにFalseを返してください.
シナリオの内容は以下の通りです．
{scenario_text}"""
        ),
    ]


@st.cache_data
def init_messages(settings: Settings):
    return [
        {"role": "system", "content": load_GM_instruction(settings)},
        {"role": "user", "content": "それではセッションを始めましょう.プレイヤーは私一人です．まずはシナリオ概要の説明と導入をお願いします."},
    ]
