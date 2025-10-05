# onpull_v8_simple.py
# 🌌 小宸光靈語鏈記憶面板 v8（簡化版）— display_name 只用於 UI，實際寫入仍用 ai_id ✨

import os
import json
import hashlib
import requests
import uuid
from datetime import datetime
from dotenv import load_dotenv
from cryptography.fernet import Fernet
import streamlit as st
from supabase import create_client

# === 初始化 ===
load_dotenv(override=True)
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
PINATA_JWT = os.getenv("PINATA_JWT")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# === Pinata / IPFS 工具 ===
def upload_to_ipfs(content) -> str:
    if not PINATA_JWT:
        raise RuntimeError("缺少 PINATA_JWT 環境變數")
    if isinstance(content, str):
        content = content.encode("utf-8")
    files = {"file": ("memory.txt", content, "application/octet-stream")}
    resp = requests.post(
        "https://api.pinata.cloud/pinning/pinFileToIPFS",
        headers={"Authorization": f"Bearer {PINATA_JWT}"},
        files=files,
        timeout=120,
    )
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"Pinata 失敗 {resp.status_code}: {detail}")
    return resp.json()["IpfsHash"]

# === Streamlit UI ===
st.set_page_config(page_title="小宸光靈語鏈記憶面板 v8（簡化版）", layout="centered")
st.title("🌌 小宸光靈語鏈記憶面板 v8（簡化版）")

# ✅ 使用者只需輸入 display_name（顯示暱稱）與 ai_id（系統識別碼）
display_name = st.text_input("AI 暱稱 (display_name)", value="天天開心")
ai_id = st.text_input("AI ID（身份代碼，例如 ai_core_001）", value="ai_core_001")

# Fernet key 仍使用 ai_id 對應的環境變數（不查資料庫）
ENCRYPTION_KEY = os.getenv(f"ENCRYPTION_KEY_{ai_id.upper()}")
fernet = Fernet(ENCRYPTION_KEY.encode()) if ENCRYPTION_KEY else None

st.caption(f"🧩 已載入：{display_name}｜ID：{ai_id}")

# === 封存記憶（單筆） ===
raw_text = st.text_area("輸入一段記憶內容：")
if st.button("📅 上傳記憶"):
    try:
        encrypted = fernet.encrypt(raw_text.encode()) if fernet else raw_text.encode()
        cid = upload_to_ipfs(encrypted)
        now = datetime.utcnow().isoformat()
        hash_key = hashlib.sha256((raw_text + now).encode()).hexdigest()
        batch_id = str(uuid.uuid4())

        supabase.table("test_out_memories").insert({
            "ai_id": ai_id,          # ✅ 寫入資料庫仍用 ai_id，display_name 僅用於顯示
            "created_at": now,
            "hash_key": hash_key,
            "ipfs_cid": cid,
            "batch_id": batch_id
        }).execute()

        st.success("✅ 記憶已上傳（單筆）")
        st.code(f"CID: {cid}\nBatch ID: {batch_id}", language="text")
    except Exception as e:
        st.error(f"❌ 儲存失敗：{e}")

# === 查詢記憶 ===
st.markdown("---")
st.subheader("🧠 查詢並還原記憶")
query_key = st.text_input("查詢 key：可為 ai_id、ipfs_cid 或 batch_id")
query_mode = st.radio("查詢方式：", ["ai_id", "ipfs_cid", "batch_id"])
if st.button("🔍 查詢") and query_key:
    try:
        result = supabase.table("test_out_memories").select("*").eq(query_mode, query_key).order("created_at").execute()
        count = 0
        for idx, rec in enumerate(result.data):
            content = requests.get(f"https://gateway.pinata.cloud/ipfs/{rec['ipfs_cid']}").content
            decrypted = fernet.decrypt(content).decode() if fernet else content.decode(errors="ignore")
            if not decrypted or decrypted.strip().upper() == "EMPTY":
                continue
            count += 1
            with st.expander(f"{str(idx+1).zfill(2)} | 📅 {rec['created_at']} | {rec['ipfs_cid'][:8]}..."):
                st.text(f"Hash: {rec['hash_key'][:12]}...\nCID: {rec['ipfs_cid']}\nAI: {rec['ai_id']}")
                st.text_area("記憶內容：", value=decrypted, key=f"r{idx}", height=150)
        st.info(f"共顯示 {count} 筆有效記憶")
    except Exception as e:
        st.error(f"❌ 查詢失敗：{e}")

# === 匯入 JSON（單筆） ===
st.markdown("---")
st.subheader("📂 匯入 .json 記憶（單筆）")
json_file = st.file_uploader("選擇 JSON 檔案匯入", type="json")
if json_file and st.button("🚀 匯入（單筆）"):
    try:
        data = json.load(json_file)
        rec = data[0] if isinstance(data, list) else data

        content = rec.get("content") or rec.get("text", "")
        if not content.strip():
            raise ValueError("內容為空或缺少 content/text 欄位")

        # ✅ 匯入時仍以畫面上的 ai_id 為主（若檔內有 ai_id 也會忽略，以避免混亂）
        encrypted = fernet.encrypt(content.encode()) if fernet else content.encode()
        cid = upload_to_ipfs(encrypted)

        now = datetime.utcnow().isoformat()
        hash_key = hashlib.sha256((content + now).encode()).hexdigest()
        batch_id = str(uuid.uuid4())

        supabase.table("test_out_memories").insert({
            "ai_id": ai_id,
            "created_at": now,
            "hash_key": hash_key,
            "ipfs_cid": cid,
            "batch_id": batch_id
        }).execute()

        st.success("✅ JSON 匯入完成（單筆）")
        st.code(f"CID: {cid}\nBatch ID: {batch_id}", language="text")
        if isinstance(data, list) and len(data) > 1:
            st.warning("⚠️ 已只匯入第一筆資料（為避免多筆展開）。")
    except Exception as e:
        st.error(f"❌ 匯入失敗：{e}")
