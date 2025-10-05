# generate_fernet_key.py
from cryptography.fernet import Fernet
import os

def generate_and_save_key():
    key = Fernet.generate_key().decode()
    file_path = os.path.join(os.getcwd(), "generated_key.txt")
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"你的 Fernet 加密金鑰：\n{key}\n")
    print(f"\n✅ 金鑰產生完成：\n{key}\n\n📂 已儲存到：{file_path}")
    input("\n按下 Enter 關閉視窗...")

if __name__ == "__main__":
    generate_and_save_key()
