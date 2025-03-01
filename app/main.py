# main.py
import os
from fastapi import FastAPI, File, UploadFile, Request, Header, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 初始化 FastAPI 应用
app = FastAPI()

# 配置模板和静态文件
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

# 定义上传和输出文件夹
app_dir = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(app_dir, 'uploads')
OUTPUT_FOLDER = os.path.join(app_dir, 'output')

# 确保文件夹存在
for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")
app.mount("/output", StaticFiles(directory=OUTPUT_FOLDER), name="output")

# 首页路由
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

import uuid
from utils.llm_utils import llm_invoke

@app.post("/chat-submit")
async def submit_chat(request: Request):
    form_data = await request.form()
    text = form_data.get('text')

    # 假設前端傳遞一個唯一的 chat_id，若無則生成新 ID
    chat_id = form_data.get('chat_id', str(uuid.uuid4()))
    response = llm_invoke('web-chat', chat_id, text)
    
    return JSONResponse(content={"result": f"AI回答:\n{response}", "chat_id": chat_id})

# 文件上傳路由
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # 將檔案保存到 UPLOAD_FOLDER
    file_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(file_path, "wb") as f:
        f.write(await file.read())
    return JSONResponse(content={"message": "File uploaded successfully", "filename": file.filename})

# 移除檔案路由
@app.post("/remove")
async def remove_file(request: Request):
    form_data = await request.form()
    filename = form_data.get('filename')
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # 檢查並刪除相關截圖
    base_filename = os.path.splitext(filename)[0]
    i = 1
    while True:
        screenshot_path = os.path.join(OUTPUT_FOLDER, f"{base_filename}_page_{i}.png")
        if os.path.exists(screenshot_path):
            os.remove(screenshot_path)
            i += 1
        else:
            break
    
    return JSONResponse(content={"message": "檔案及其截圖已移除"})
    
@app.get("/files")
async def get_uploaded_files():
    try:
        files = os.listdir(UPLOAD_FOLDER)  # 讀取 UPLOAD_FOLDER 中的檔案列表
        return JSONResponse(content={"files": files})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

from utils.ocr_utils import generate_pdf_thumbnails, get_existing_thumbnails

# 截圖處理路由
@app.post("/screenshot")
async def screenshot_files(request: Request):
    form_data = await request.form()
    filename = form_data.get('file_path')
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    
    if not os.path.exists(file_path):
        return JSONResponse(content={"error": "檔案不存在"}, status_code=404)
    
    if file_path.lower().endswith('.pdf'):
        # 檢查是否已有截圖
        existing_thumbnails = get_existing_thumbnails(filename, OUTPUT_FOLDER)
        if existing_thumbnails:
            return JSONResponse(content={"thumbnails": existing_thumbnails})
        # 若無現有截圖，生成新截圖
        thumbnail_paths = generate_pdf_thumbnails(file_path, OUTPUT_FOLDER)
        return JSONResponse(content={"thumbnails": thumbnail_paths})
    else:
        return JSONResponse(content={"thumbnails": [f"/uploads/{filename}"]})


# LINE-BOT路由

from utils.line_bot_handler import handle_line_ask_message, handle_line_assistant_message

@app.post("/ask")
async def call_ask(request: Request, x_line_signature: str = Header(None)):
    signature = x_line_signature
    body = await request.body()
    body_str = body.decode('utf-8')
    print("Request body:", body_str)

    try:
        handle_line_ask_message(body_str, signature)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error handling Line message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return "OK"

@app.post("/assistant")
async def call_assistant(request: Request, x_line_signature: str = Header(None)):
    signature = x_line_signature
    body = await request.body()
    body_str = body.decode('utf-8')
    print("Request body:", body_str)

    try:
        handle_line_assistant_message(body_str, signature)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error handling Line assistant message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return "OK"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
