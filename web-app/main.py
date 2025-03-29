from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.requests import Request
import whisper
import google.generativeai as genai
from pathlib import Path
import os
from dotenv import load_dotenv
import tempfile
import json
from datetime import datetime

# 載入環境變數
load_dotenv()

# 設定 Google API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
if not GOOGLE_API_KEY:
    raise ValueError("請設定 GOOGLE_API_KEY 環境變數")
genai.configure(api_key=GOOGLE_API_KEY)

# 初始化 Whisper 模型（使用最小的模型以節省資源）
whisper_model = whisper.load_model("tiny")

# 創建 FastAPI 應用
app = FastAPI(title="音訊摘要生成器")

# 設定靜態文件和模板
BASE_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# 確保上傳目錄存在
UPLOAD_DIR = BASE_DIR / "static/uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 歷史記錄文件
HISTORY_FILE = UPLOAD_DIR / "history.json"
if not HISTORY_FILE.exists():
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, ensure_ascii=False)

def load_history():
    """載入歷史記錄"""
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_history(history):
    """保存歷史記錄"""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def generate_summary(transcript: str) -> dict:
    """使用 Gemini 生成摘要和執行計劃"""
    try:
        print(f"使用的 API 金鑰: {GOOGLE_API_KEY}")  # 添加調試信息
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # 生成摘要
        summary_prompt = f"""
        請針對以下音訊逐字稿生成一份清晰的重點摘要。摘要需要：
        1. 包含音訊的主要內容
        2. 列出重要的觀點
        3. 標明需要注意的重點
        4. 使用條列式格式，讓內容更容易閱讀
        5. 請不要使用任何 Markdown 符號（如 *、# 等）

        音訊逐字稿內容：
        {transcript}
        """
        try:
            summary_response = model.generate_content(summary_prompt)
            print("摘要生成成功")  # 添加調試信息
        except Exception as e:
            print(f"摘要生成失敗: {str(e)}")  # 添加調試信息
            raise
        
        # 生成執行計劃
        action_prompt = f"""
        根據以下音訊摘要，請生成一份詳細的執行計劃。計劃需要：
        1. 列出具體的執行步驟
        2. 標明每個步驟的優先順序
        3. 建議合理的時間安排
        4. 提供執行建議和注意事項
        5. 請不要使用任何 Markdown 符號（如 *、# 等）

        音訊摘要內容：
        {summary_response.text}
        """
        action_response = model.generate_content(action_prompt)
        
        # 移除可能的 Markdown 符號
        summary_text = summary_response.text.replace('*', '').replace('#', '')
        action_text = action_response.text.replace('*', '').replace('#', '')
        
        return {
            "summary": summary_text,
            "action_plan": action_text
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成摘要時發生錯誤: {str(e)}")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """處理音訊檔案上傳"""
    try:
        # 檢查檔案類型
        if not file.filename.lower().endswith('.mp3'):
            raise HTTPException(status_code=400, detail="只接受 MP3 檔案")
            
        # 生成唯一的檔案名稱
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_name = file.filename.rsplit('.', 1)[0]
        new_filename = f"{original_name}_{timestamp}.mp3"
            
        # 保存原始音訊檔案
        file_path = UPLOAD_DIR / new_filename
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
            
        # 使用 Whisper 進行轉錄
        result = whisper_model.transcribe(str(file_path))
        transcript = result["text"]
        
        # 生成摘要和執行計劃
        result = generate_summary(transcript)
        
        # 保存到歷史記錄
        history = load_history()
        history.insert(0, {
            "filename": new_filename,
            "original_name": file.filename,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "transcript": transcript,
            "summary": result["summary"],
            "action_plan": result["action_plan"]
        })
        save_history(history)
        
        return result
            
    except Exception as e:
        # 如果發生錯誤，清理已上傳的檔案
        if 'file_path' in locals() and file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def home(request: Request):
    """首頁"""
    try:
        return templates.TemplateResponse(
            "index.html",
            {"request": request}
        )
    except Exception as e:
        print(f"Error rendering template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_history(request: Request):
    """歷史記錄頁面"""
    try:
        return templates.TemplateResponse(
            "history.html",
            {
                "request": request,
                "history": load_history()
            }
        )
    except Exception as e:
        print(f"Error rendering template: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/delete/{filename}")
async def delete_record(filename: str):
    """刪除記錄"""
    try:
        # 讀取歷史記錄
        history = load_history()
        
        # 找到要刪除的記錄
        history = [item for item in history if item["filename"] != filename]
        
        # 保存更新後的歷史記錄
        save_history(history)
        
        # 刪除音訊檔案
        file_path = UPLOAD_DIR / filename
        if file_path.exists():
            file_path.unlink()
            
        return {"message": "記錄已刪除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000) 