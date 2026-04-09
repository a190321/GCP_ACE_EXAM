☁️ GCP ACE 雲端架構師刷題系統 (Serverless Exam Practice Platform)
這是一個專為準備 Google Cloud Associate Cloud Engineer (ACE) 考試所設計的「無伺服器架構 (Serverless)」刷題系統。

本專案將前端部署於 Google Sites，後端採用 FastAPI 並運行於 Cloud Run，結合 Firebase Authentication 與 Firestore，打造出一個具備身分驗證、個人化錯題本、狀態標記與智慧篩選的輕量級線上學習平台。

✨ 核心功能 (Features)
🔐 安全身分驗證 (Google Sign-In)：整合 Firebase Auth，支援多使用者獨立登入，資料互不干擾。

📊 個人化學習進度 (Progress Tracking)：自動記錄每位使用者的答對、答錯紀錄。

🏷️ 狀態標記系統 (Tagging System)：

⭐ 不太熟：標記需要重點複習的題目。

✅ 我會了：標記已完全掌握的題目。

🔍 智慧過濾器 (Smart Filter)：支援「隱藏已答對」、「隱藏我會了」、「只看錯題」、「只看不太熟」，打造最高效的衝刺模式。

📝 專屬筆記本 (Personal Notes)：每道題目皆可獨立新增、儲存個人筆記。

🏗️ 系統架構與技術棧 (Tech Stack)
本專案完全遵循 Google Cloud 最佳實踐，採用全託管與無伺服器服務：

前端 (Frontend)：Vanilla HTML / JavaScript / CSS

部署位置：Google Sites (透過 iframe 嵌入)

身分驗證：Firebase Authentication SDK (採用 Redirect 跳轉登入機制以突破沙箱限制)

後端 (Backend)：Python 3.10+ / FastAPI

部署位置：Google Cloud Run (自動擴展、按需計費)

身分驗證攔截：JWT Token 驗證機制 (HTTPBearer)

資料庫 (Database)：Cloud Firestore (NoSQL 資料庫，儲存題庫與使用者進度)

安全性 (Security)：Secret Manager (安全儲存 Firebase Admin SDK 金鑰)

📂 資料庫設計 (Database Schema)
questions (Collection): 存放所有題庫 (包含題號、題目、選項、正確答案)。

user_progress (Collection): 記錄使用者作答狀態 (包含 user_id, question_id, is_correct, is_mastered, is_unfamiliar)。

user_notes (Collection): 記錄使用者針對單一題目的筆記。

🚀 部署指南 (Deployment Guide)
1. 後端部署 (Cloud Run)
在 GCP 專案中啟用 Cloud Run, Firestore, Secret Manager API。

下載 Firebase Admin SDK JSON 金鑰，並將內容上傳至 Secret Manager（命名為 firebase-key）。

使用 gcloud 指令或 Cloud Build 將 FastAPI 程式碼封裝成 Docker Image 並部署至 Cloud Run。

於 Cloud Run 設定環境變數 FIREBASE_SECRET_PATH 指向 Secret Manager 的最新版本路徑：

Plaintext
projects/你的專案ID/secrets/firebase-key/versions/latest
2. 前端部署 (Google Sites)
在 Firebase Console > Authentication > Settings > Authorized domains 中，加入以下網域以允許 Google Sites 登入：

sites.google.com

googleusercontent.com (因應 Google Sites 動態 iframe 沙箱機制)

複製專案中的 HTML/JS 程式碼。

將程式碼中的 API_BASE_URL 修改為你的 Cloud Run 網址。

將 firebaseConfig 替換為你的 Firebase 專案設定檔。

於 Google Sites 中使用「嵌入 > 嵌入程式碼」貼上程式碼並發布。

🔒 API 授權機制 (API Security)
後端 API 採用 Firebase JWT Token 進行驗證。前端在發送請求時，需將 Token 附帶於 HTTP Header 中：

HTTP
Authorization: Bearer <YOUR_FIREBASE_ID_TOKEN>
FastAPI 後端會透過 firebase_admin.auth.verify_id_token 驗證 Token 合法性，並提取出真實的 uid 進行資料庫操作，確保使用者無法竄改他人資料。


👨‍💻 開發者 (Author)

Name: 林怡妏 / a1903

Role: Data Engineer / Cloud Architect

Contact: a190321@gmail.com

(本專案為準備 GCP ACE 認證之實作練習)
