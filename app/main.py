# main.py
"""
FastAPI 應用主程式，提供檔案上傳、聊天功能及 Line Bot 服務。
"""

import os
import uuid
from typing import List

from fastapi import FastAPI, File, UploadFile, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from utils.llm_utils import llm_invoke
from utils.ocr_utils import generate_pdf_thumbnails, get_existing_thumbnails
from utils.line_bot_handler import handle_line_ask_message, handle_line_assistant_message

# 初始化 FastAPI 應用
app = FastAPI(title="Chat and File Management API")

# 配置模板和靜態檔案
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
TEMPLATES = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 定義上傳和輸出資料夾
APP_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(APP_DIR, 'uploads')
OUTPUT_FOLDER = os.path.join(APP_DIR, 'output')

# 確保資料夾存在
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")
app.mount("/output", StaticFiles(directory=OUTPUT_FOLDER), name="output")

# 首頁路由
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request) -> HTMLResponse:
    """渲染首頁 HTML。

    Args:
        request (Request): FastAPI 請求對象。

    Returns:
        HTMLResponse: 渲染後的首頁內容。
    """
    return TEMPLATES.TemplateResponse("index.html", {"request": request})

# 聊天提交路由
@app.post("/chat-submit")
async def submit_chat(request: Request) -> JSONResponse:
    """處理聊天提交並返回 AI 回應。

    Args:
        request (Request): FastAPI 請求對象，包含表單數據。

    Returns:
        JSONResponse: 包含 AI 回應和聊天 ID 的 JSON 響應。
    """
    form_data = await request.form()
    text = form_data.get('text')
    chat_id = form_data.get('chat_id', str(uuid.uuid4()))
    response = llm_invoke('web-chat', chat_id, text)
    return JSONResponse(content={"result": f"AI回答:\n{response}", "chat_id": chat_id})

# 檔案上傳路由
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)) -> JSONResponse:
    """上傳檔案並儲存到 UPLOAD_FOLDER。

    Args:
        file (UploadFile): 上傳的檔案。

    Returns:
        JSONResponse: 上傳成功的訊息與檔案名稱。
    """
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as file_handle:
        file_handle.write(await file.read())
    return JSONResponse(content={"message": "File uploaded successfully", "filename": file.filename})

# 移除檔案路由
@app.post("/remove")
async def remove_file(request: Request) -> JSONResponse:
    """移除指定檔案及其相關截圖。

    Args:
        request (Request): FastAPI 請求對象，包含表單數據。

    Returns:
        JSONResponse: 移除成功的訊息。
    """
    form_data = await request.form()
    filename = form_data.get('filename')
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    if os.path.exists(file_path):
        os.remove(file_path)

    # 移除相關截圖
    base_filename = os.path.splitext(filename)[0]
    page_num = 1
    while True:
        screenshot_path = os.path.join(OUTPUT_FOLDER, f"{base_filename}_page_{page_num}.png")
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
            page_num += 1
        else:
            break

    return JSONResponse(content={"message": "檔案及其截圖已移除"})

# 獲取已上傳檔案列表
@app.get("/files")
async def get_uploaded_files() -> JSONResponse:
    """獲取 UPLOAD_FOLDER 中的檔案列表。

    Returns:
        JSONResponse: 包含檔案列表或錯誤訊息的 JSON 響應。
    """
    try:
        files: List[str] = os.listdir(UPLOAD_FOLDER)
        return JSONResponse(content={"files": files})
    except Exception as error:
        return JSONResponse(content={"error": str(error)}, status_code=500)

# 截圖處理路由
@app.post("/screenshot")
async def screenshot_files(request: Request) -> JSONResponse:
    """處理檔案截圖，支援 PDF 和其他格式。

    Args:
        request (Request): FastAPI 請求對象，包含表單數據。

    Returns:
        JSONResponse: 包含截圖路徑或錯誤訊息的 JSON 響應。
    """
    form_data = await request.form()
    filename = form_data.get('file_path')
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(file_path):
        return JSONResponse(content={"error": "檔案不存在"}, status_code=404)

    if file_path.lower().endswith('.pdf'):
        existing_thumbnails = get_existing_thumbnails(filename, OUTPUT_FOLDER)
        if existing_thumbnails:
            return JSONResponse(content={"thumbnails": existing_thumbnails})
        thumbnail_paths = generate_pdf_thumbnails(file_path, OUTPUT_FOLDER)
        return JSONResponse(content={"thumbnails": thumbnail_paths})
    return JSONResponse(content={"thumbnails": [f"/uploads/{filename}"]})

# LINE-BOT 路由
@app.post("/ask")
async def call_ask(request: Request, x_line_signature: str = Header(None)) -> str:
    """處理 Line Bot 的問答請求。

    Args:
        request (Request): FastAPI 請求對象。
        x_line_signature (str): Line 的簽名頭部。

    Returns:
        str: "OK" 表示成功處理。
    """
    signature = x_line_signature
    body = await request.body()
    body_str = body.decode('utf-8')
    print("Request body:", body_str)

    try:
        handle_line_ask_message(body_str, signature)
    except HTTPException as error:
        raise error
    except Exception as error:
        print(f"Error handling Line message: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return "OK"

@app.post("/assistant")
async def call_assistant(request: Request, x_line_signature: str = Header(None)) -> str:
    """處理 Line Bot 的助理請求。

    Args:
        request (Request): FastAPI 請求對象。
        x_line_signature (str): Line 的簽名頭部。

    Returns:
        str: "OK" 表示成功處理。
    """
    signature = x_line_signature
    body = await request.body()
    body_str = body.decode('utf-8')
    print("Request body:", body_str)

    try:
        handle_line_assistant_message(body_str, signature)
    except HTTPException as error:
        raise error
    except Exception as error:
        print(f"Error handling Line assistant message: {error}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return "OK"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
