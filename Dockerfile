# 使用輕量級 Python 鏡像
FROM python:3.9-slim

# 設定工作目錄
WORKDIR /app

# 複製依賴清單並安裝
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有程式碼（包含你的 Firebase 金鑰 JSON）
COPY . .

# Cloud Run 預設監聽 8080 埠
EXPOSE 8080

# 啟動 FastAPI (注意：port 必須是 8080)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]