import fitz  # PyMuPDFのインポート
import tkinter as tk
from tkinter import filedialog

def extract_text_from_pdf(pdf_path):
    # PDFファイルを開く
    document = fitz.open(pdf_path)
    text = ""
    
    # 各ページを巡回してテキストを抽出
    for page_num in range(len(document)):
        page = document.load_page(page_num)
        text += page.get_text()
    
    # 改行をスペースに置き換える
    cleaned_text = text.replace('\n', ' ').replace('\r', '')
    # 複数のスペースを1つのスペースに置き換える
    cleaned_text = ' '.join(cleaned_text.split())
    
    return cleaned_text

# ファイル選択ダイアログを表示する関数
def select_file():
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを表示しない
    file_path = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
    return file_path

# 使用例
pdf_path = select_file()
if pdf_path:
    extracted_text = extract_text_from_pdf(pdf_path)
    print(extracted_text)
    # テキストファイルに保存
    with open("extracted_text.txt", "w") as f:
        f.write(extracted_text)
        
else:
    print("ファイルが選択されませんでした。")
