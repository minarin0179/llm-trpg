import discord

# 必要なインテントを設定
intents = discord.Intents.default()
intents.message_content = True

# クライアントのインスタンスを作成
client = discord.Client(intents=intents)


@client.event
async def on_ready():
    print(f'ログインしました: {client.user}')


@client.event
async def on_message(message):
    # ボット自身のメッセージには反応しない
    if message.author == client.user:
        return

    # メッセージが "ping" の場合に "pong" と応答
    if message.content.lower() == 'ping':
        await message.channel.send('pong')

    messages = []
    # そのチャンネルのメッセージをすべて取得
    if message.content.lower() == 'get':
        async for message in message.channel.history(limit=200):
            if message.author == client.user:
                messages.append(
                    {"role": "assistant", "content": message.content})
            else:
                messages.append(
                    {"role": "user", "content": message.content})
    messages.reverse()
    print(messages)

# ボットのトークンを指定して起動
client.run(
    'MTI5OTI1MDg0OTEzODA4NTkxOA.GykJdG.jvsD3YhQeFjbfFMG36AvKTzTt-qlN8DVNTo8ts')
