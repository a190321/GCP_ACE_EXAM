from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import os
from google.cloud import secretmanager
import json



# 強制讀取環境變數，如果不指定就用本機測試的檔名
FIREBASE_SECRET_PATH = os.environ.get("FIREBASE_SECRET_PATH")

def get_firebase_key():
    if not FIREBASE_SECRET_PATH:
        print("❌ [錯誤] 沒有設定環境變數 FIREBASE_SECRET_PATH")
        # 如果是本機測試，可以直接回傳本機檔案的 JSON 內容 (選用)
        return None

    try:
        print(f"🔍 嘗試存取 Secret: {FIREBASE_SECRET_PATH}")
        client = secretmanager.SecretManagerServiceClient()
        response = client.access_secret_version(request={"name": FIREBASE_SECRET_PATH})
        payload = response.payload.data.decode("UTF-8")
        return json.loads(payload)
    except Exception as e:
        print(f"❌ [嚴重錯誤] 讀取 Secret Manager 失敗: {e}")
        return None

# 初始化 Firebase
key_dict = get_firebase_key()

if key_dict:
    print("✅ 成功讀取金鑰，準備初始化 Firebase...")
    cred = credentials.Certificate(key_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase DB 連線成功！")
else:
    print("⚠️ 警告: db 設為 None。接下來的 API 呼叫將會失敗。")
    db = None

# --- 初始化區 ---
print("🚀 正在啟動應用程式並初始化 Firebase...")
key_dict = get_firebase_key()

if key_dict:
    cred = credentials.Certificate(key_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase 初始化成功！")
else:
    print("⚠️ Firebase 初始化跳過（將導致後端功能失效），請檢查權限與路徑。")
    # 這裡不讓程式崩潰，而是讓它跑起來，你才能看到上面的 Print 訊息
    db = None

# 1. 初始化 Firebase (請記得把金鑰檔名換成你自己的)
# cred = credentials.Certificate("firebase_key.json")
# if not firebase_admin._apps:
#     firebase_admin.initialize_app(cred)

# db = firestore.client()
app = FastAPI()

# 2. 設定 CORS (非常重要！這樣 Google Sites 的前端才能跨網域呼叫這支 API)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # 允許所有來源
    allow_credentials=True,      # 允許攜帶 Cookie (如果未來需要)
    allow_methods=["*"],         # 允許所有方法 (GET, POST, OPTIONS 等)
    allow_headers=["*"],         # 允許所有標頭
)

# 定義接收筆記資料的格式
class NoteRequest(BaseModel):
    user_id: str
    question_id: str
    content: str

# 1. 紀錄作答結果
class ProgressRequest(BaseModel):
    user_id: str
    question_id: str
    is_correct: bool

@app.post("/api/record-progress")
def record_progress(data: ProgressRequest):
    doc_id = f"{data.user_id}_{data.question_id}"
    doc_ref = db.collection('user_progress').document(doc_id)
    doc_ref.set({
        "user_id": data.user_id,
        "question_id": data.question_id,
        "is_correct": data.is_correct,
        "last_answered_at": datetime.now().isoformat()
    })
    return {"status": "success"}

# 2. 獲取該使用者的所有錯題 ID
@app.get("/api/wrong-question-ids")
def get_wrong_question_ids(user_id: str):
    # 查詢該用戶所有 is_correct 為 false 的紀錄
    docs = db.collection('user_progress') \
             .where('user_id', '==', user_id) \
             .where('is_correct', '==', False).stream()
    
    wrong_ids = sorted([doc.to_dict()['question_id'] for doc in docs])
    return {"status": "success", "ids": wrong_ids}

# API: 取得所有題目的 ID 清單
@app.get("/api/question-ids")
def get_all_question_ids():
    try:
        # 取得 questions 集合中所有的文件
        docs = db.collection('questions').stream()
        # 收集所有的 Document ID 並排序（確保題號順序正確）
        ids = sorted([doc.id for doc in docs])
        return {"status": "success", "ids": ids}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    


# API: 取得單一題目
@app.get("/api/questions/{q_id}")
def get_question(q_id: str):
    try:
        # 1. 指定集合與文件 ID
        doc_ref = db.collection('questions').document(q_id)
        doc = doc_ref.get()
        
        # 2. 檢查文件是否存在
        if not doc.exists:
            return {"status": "error", "message": f"找不到題號：{q_id}"}
            
        # 3. 轉換為字典格式
        data = doc.to_dict()
        
        # 4. 回傳成功結果
        return {"status": "success", "data": data}
        
    except Exception as e:
        # 如果發生任何 Python 錯誤，把它轉成 JSON 回傳，避免直接跳 500 崩潰
        return {"status": "error", "message": f"後端解析錯誤: {str(e)}"}

# API: 取得使用者的筆記
@app.get("/api/notes")
def get_note(user_id: str, question_id: str):
    doc_id = f"{user_id}_{question_id}"
    doc_ref = db.collection('user_notes').document(doc_id)
    doc = doc_ref.get()
    if doc.exists:
        return {"status": "success", "data": doc.to_dict()}
    return {"status": "not_found", "data": {"content": ""}}

# API: 儲存或更新筆記
@app.post("/api/notes")
def save_note(note: NoteRequest):
    doc_id = f"{note.user_id}_{note.question_id}"
    doc_ref = db.collection('user_notes').document(doc_id)
    doc_ref.set({
        "user_id": note.user_id,
        "question_id": note.question_id,
        "content": note.content,
        "updated_at": datetime.now().isoformat()
    })
    return {"status": "success", "message": "筆記已成功儲存"}

# 1. 更新題目「不太熟」的狀態
class UnfamiliarRequest(BaseModel):
    user_id: str
    question_id: str
    is_unfamiliar: bool

@app.post("/api/update-unfamiliar")
def update_unfamiliar(data: UnfamiliarRequest):
    doc_id = f"{data.user_id}_{data.question_id}"
    doc_ref = db.collection('user_progress').document(doc_id)
    
    # 使用 merge=True，確保只更新這個欄位，不影響 is_correct 等其他資料
    doc_ref.set({
        "user_id": data.user_id,
        "question_id": data.question_id,
        "is_unfamiliar": data.is_unfamiliar
    }, merge=True)
    return {"status": "success"}

# 2. 獲取所有「不太熟」的題目 ID
@app.get("/api/unfamiliar-question-ids")
def get_unfamiliar_ids(user_id: str):
    docs = db.collection('user_progress') \
             .where('user_id', '==', user_id) \
             .where('is_unfamiliar', '==', True).stream()
    
    ids = sorted([doc.to_dict()['question_id'] for doc in docs])
    return {"status": "success", "ids": ids}




if __name__ == "__main__":
    # 讀取環境變數 PORT，如果沒有則預設 8080
    port = int(os.environ.get("PORT", 8080))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=port)

@app.get("/")
def read_root():
    return {"message": "GCP ACE Exam API is running!", "status": "healthy"}