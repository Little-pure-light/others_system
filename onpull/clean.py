import os
import requests
from dotenv import load_dotenv

load_dotenv()

PINATA_JWT = os.getenv("PINATA_JWT")
if not PINATA_JWT:
    raise RuntimeError("❌ 請先在 .env 設定 PINATA_JWT")

headers = {
    "Authorization": f"Bearer {PINATA_JWT}",
    "Content-Type": "application/json"
}

base_url = "https://api.pinata.cloud/v3/files"

def list_files(page_token=None, limit=100, visibility="public"):
    url = f"{base_url}?limit={limit}&visibility={visibility}"
    if page_token:
        url += f"&page_token={page_token}"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()

def delete_file(file_id):
    url = f"{base_url}/{file_id}"
    r = requests.delete(url, headers=headers)
    if r.status_code == 200:
        print(f"✅ 已刪除 file_id={file_id}")
    else:
        print(f"⚠️ 刪除失敗 file_id={file_id}: {r.text}")

def clean_all(visibility="public"):
    total_deleted = 0
    page_token = None

    while True:
        data = list_files(page_token=page_token, limit=100, visibility=visibility)
        files = data.get("data", {}).get("files", [])
        page_token = data.get("data", {}).get("next_page_token")

        if not files:
            break

        for f in files:
            print(f"🗑 準備刪除：{f}")
            delete_file(f["id"])
            total_deleted += 1

        if not page_token:
            break

    print(f"\n🎉 [{visibility}] 全部刪除完成！共刪除 {total_deleted} 筆。")

if __name__ == "__main__":
    # 可自行切換或都執行
    clean_all("public")   # 刪除 Public
    clean_all("private")  # 刪除 Private
