from utils.notion import save_to_notion


contents = '{"key": "value", "data": ["item1", "item2"]}' * 500  # 大量データ

save_to_notion("Code Content Page", contents)
