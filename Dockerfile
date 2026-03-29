# 1. 使用穩定的 Python 版本
FROM python:3.11-slim

# 2. 設定工作目錄
WORKDIR /app

# 3. 先複製清單並安裝套件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. 複製所有程式碼
COPY . .

# 5. 使用 python -m 指令確保能正確啟動 uvicorn
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]