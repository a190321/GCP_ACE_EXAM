from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore, auth
from datetime import datetime
import os
from google.cloud import secretmanager
import json
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import uvicorn

# ==========================================
# 1. 系統與 Firebase 初始化區塊
# ==========================================
FIREBASE_SECRET_PATH = os.environ.get("FIREBASE_SECRET_PATH")

def get_firebase_key():
    if not FIREBASE_SECRET_PATH:
        print("❌ [錯誤] 沒有設定環境變數 FIREBASE_SECRET_PATH")
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

print("🚀 正在啟動應用程式並初始化 Firebase...")
key_dict = get_firebase_key()

if key_dict:
    print("✅ 成功讀取金鑰，準備初始化 Firebase...")
    cred = credentials.Certificate(key_dict)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("✅ Firebase DB 連線成功！")
else:
    print("⚠️ 警告: db 設為 None。接下來的資料庫呼叫將會失敗。")
    db = None

app = FastAPI()

# 設定 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# 2. 安全認證機制 (數位警衛)
# ==========================================
security = HTTPBearer()

def verify_user_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token['uid']
        return uid
    except Exception as e:
        print(f"❌ Token 驗證失敗: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無效的憑證或登入已過期",
        )

# ==========================================
# 3. Request Body 定義 (移除 user_id，因為改由 Token 提供)
# ==========================================
class NoteRequest(BaseModel):
    # user_id: str  <-- 移除了
    question_id: str
    content: str

class ProgressRequest(BaseModel):
    # user_id: str  <-- 移除了
    question_id: str
    is_correct: bool

class UnfamiliarRequest(BaseModel):
    # user_id: str  <-- 移除了
    question_id: str
    is_unfamiliar: bool

# ==========================================
# 4. API 路由 (需要登入的加上 uid: str = Depends(verify_user_token))
# ==========================================

@app.get("/")
def read_root():
    return {"message": "GCP ACE Exam API is running with Auth!", "status": "healthy"}

# --- 公開 API (不需要登入就能看題目) ---

@app.get("/api/question-ids")
def get_all_question_ids():
    try:
        docs = db.collection('questions').stream()
        ids = sorted([doc.id for doc in docs])
        return {"status": "success", "ids": ids}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/questions/{q_id}")
def get_question(q_id: str):
    try:
        doc_ref = db.collection('questions').document(q_id)
        doc = doc_ref.get()
        if not doc.exists:
            return {"status": "error", "message": f"找不到題號：{q_id}"}
        return {"status": "success", "data": doc.to_dict()}
    except Exception as e:
        return {"status": "error", "message": f"後端解析錯誤: {str(e)}"}

# --- 私有 API (需要登入才能操作個人資料) ---

@app.post("/api/record-progress")
def record_progress(data: ProgressRequest, uid: str = Depends(verify_user_token)):
    doc_id = f"{uid}_{data.question_id}"
    doc_ref = db.collection('user_progress').document(doc_id)
    doc_ref.set({
        "user_id": uid, # 使用解析出來的真實 UID
        "question_id": data.question_id,
        "is_correct": data.is_correct,
        "last_answered_at": datetime.now().isoformat()
    })
    return {"status": "success"}

@app.get("/api/wrong-question-ids")
def get_wrong_question_ids(uid: str = Depends(verify_user_token)):
    docs = db.collection('user_progress') \
             .where('user_id', '==', uid) \
             .where('is_correct', '==', False).stream()
    wrong_ids = sorted([doc.to_dict()['question_id'] for doc in docs])
    return {"status": "success", "ids": wrong_ids}

@app.get("/api/notes")
def get_note(question_id: str, uid: str = Depends(verify_user_token)):
    doc_id = f"{uid}_{question_id}"
    doc_ref = db.collection('user_notes').document(doc_id)
    doc = doc_ref.get()
    if doc.exists:
        return {"status": "success", "data": doc.to_dict()}
    return {"status": "not_found", "data": {"content": ""}}

@app.post("/api/notes")
def save_note(note: NoteRequest, uid: str = Depends(verify_user_token)):
    doc_id = f"{uid}_{note.question_id}"
    doc_ref = db.collection('user_notes').document(doc_id)
    doc_ref.set({
        "user_id": uid,
        "question_id": note.question_id,
        "content": note.content,
        "updated_at": datetime.now().isoformat()
    })
    return {"status": "success", "message": "筆記已成功儲存"}

@app.post("/api/update-unfamiliar")
def update_unfamiliar(data: UnfamiliarRequest, uid: str = Depends(verify_user_token)):
    doc_id = f"{uid}_{data.question_id}"
    doc_ref = db.collection('user_progress').document(doc_id)
    doc_ref.set({
        "user_id": uid,
        "question_id": data.question_id,
        "is_unfamiliar": data.is_unfamiliar
    }, merge=True)
    return {"status": "success"}

@app.get("/api/unfamiliar-question-ids")
def get_unfamiliar_ids(uid: str = Depends(verify_user_token)):
    docs = db.collection('user_progress') \
             .where('user_id', '==', uid) \
             .where('is_unfamiliar', '==', True).stream()
    ids = sorted([doc.to_dict()['question_id'] for doc in docs])
    return {"status": "success", "ids": ids}

# ==========================================
# 5. 啟動區塊
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)