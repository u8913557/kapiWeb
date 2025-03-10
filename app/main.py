# main.py
"""
FastAPI 應用主程式，提供檔案上傳、聊天功能及 Line Bot 服務。
"""

import shutil
import uuid
import logging
import asyncio
from typing import Dict
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Request, Header, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from utils.llm_utils import llm_invoke
from utils.ocr_utils import generate_pdf_thumbnails, get_existing_thumbnails, docling_extract_text_from_file, extract_text_from_file
from utils.line_bot_handler import handle_line_ask_message, handle_line_assistant_message
from utils.redis_utils import init_redis_pool, close_redis_pool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 生命週期事件處理器
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動事件
    await init_redis_pool()
    yield
    # 關閉事件
    await close_redis_pool()

# 初始化 FastAPI 應用，使用 lifespan
app = FastAPI(title="Chat and File Management API", lifespan=lifespan)

# 配置模板和靜態檔案
BASE_DIR = Path(__file__).parent.absolute()
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
TEMPLATES = Jinja2Templates(directory=BASE_DIR / "templates")

# 定義上傳和輸出資料夾
APP_DIR = Path(__file__).parent.absolute()
UPLOAD_FOLDER = APP_DIR / "uploads"
OUTPUT_FOLDER = APP_DIR / "output"

for folder in [UPLOAD_FOLDER, OUTPUT_FOLDER]:
    folder.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=UPLOAD_FOLDER), name="uploads")
app.mount("/output", StaticFiles(directory=OUTPUT_FOLDER), name="output")

# 全域變數追蹤 RAG 處理狀態
rag_status: Dict[str, bool] = {}

# WebSocket 連線管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, filename: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[filename] = websocket

    async def disconnect(self, filename: str):
        if filename in self.active_connections:
            del self.active_connections[filename]

    async def send_status(self, filename: str, is_complete: bool):
        if filename in self.active_connections:
            await self.active_connections[filename].send_json({"filename": filename, "is_complete": is_complete})

manager = ConnectionManager()

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
    logging.info(f"聊天提交: {text}, chat_id: {chat_id}")
    response = await llm_invoke('web-chat', chat_id, text)
    logging.info(f"聊天回應完成: {response}")
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
    file_path = UPLOAD_FOLDER / file.filename
    with file_path.open("wb") as file_handle:
        file_handle.write(await file.read())
    
    base_filename = Path(file.filename).stem
    output_subfolder = OUTPUT_FOLDER / base_filename
    txt_exists = (output_subfolder / f"{base_filename}_full_text.txt").exists()
    is_rag_processed = txt_exists
    
    return JSONResponse(content={
        "message": "File uploaded successfully",
        "filename": file.filename,
        "is_rag_processed": is_rag_processed
    })

# 移除檔案路由
@app.post("/remove")
async def remove_file(request: Request) -> JSONResponse:
    """移除指定檔案及其相關輸出子目錄。

    Args:
        request (Request): FastAPI 請求對象，包含表單數據。

    Returns:
        JSONResponse: 移除成功的訊息。
    """
    form_data = await request.form()
    filename = form_data.get('filename')
    file_path = UPLOAD_FOLDER / filename

    if file_path.exists():
        file_path.unlink()
    else:
        logging.warning(f"移除時檔案不存在: {file_path}")

    base_filename = Path(filename).stem
    output_subfolder = OUTPUT_FOLDER / base_filename
    if output_subfolder.exists() and output_subfolder.is_dir():
        shutil.rmtree(output_subfolder)
        logging.info(f"已移除輸出子目錄: {output_subfolder}")
    
    return JSONResponse(content={"message": "檔案及其相關輸出已移除"})

# 獲取已上傳檔案列表
@app.get("/files")
async def get_uploaded_files() -> JSONResponse:
    """獲取 UPLOAD_FOLDER 中的檔案列表及其 RAG 處理狀態。

    Returns:
        JSONResponse: 包含檔案列表及其狀態的 JSON 響應。
    """
    try:
        files = []
        for f in UPLOAD_FOLDER.iterdir():
            if f.is_file():
                base_filename = f.stem
                output_subfolder = OUTPUT_FOLDER / base_filename
                txt_exists = (output_subfolder / f"{base_filename}_full_text.txt").exists()
                is_rag_processed = txt_exists
                files.append({
                    "filename": f.name,
                    "is_rag_processed": is_rag_processed
                })
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

    if not filename or filename is None:
        logging.error("未提供文件名或文件名為 None")
        return JSONResponse(content={"error": "未提供有效的文件名"}, status_code=400)

    file_path = UPLOAD_FOLDER / filename

    if not file_path.exists():
        logging.error(f"檔案不存在: {file_path}")
        return JSONResponse(content={"error": f"檔案不存在: {file_path}"}, status_code=404)

    base_filename = Path(filename).stem
    output_subfolder = OUTPUT_FOLDER / base_filename

    if file_path.suffix.lower() == '.pdf':
        existing_thumbnails = get_existing_thumbnails(filename, str(output_subfolder))
        if existing_thumbnails:
            return JSONResponse(content={"thumbnails": existing_thumbnails})
        thumbnail_paths = generate_pdf_thumbnails(str(file_path), str(output_subfolder))
        return JSONResponse(content={"thumbnails": thumbnail_paths})
    return JSONResponse(content={"thumbnails": [f"/uploads/{filename}"]})

# RAG 處理路由
@app.post("/rag")
async def rag_files(request: Request, background_tasks: BackgroundTasks) -> JSONResponse:
    data = await request.json()
    filename = data.get("filename")
    if not filename:
        logging.error("未提供文件名")
        return JSONResponse({"error": "未提供文件名"}, status_code=400)
    
    file_location = UPLOAD_FOLDER / filename
    base_filename = Path(filename).stem
    output_subfolder = OUTPUT_FOLDER / base_filename
    
    if not file_location.exists():
        logging.error(f"檔案不存在: {file_location}")
        return JSONResponse({"error": f"檔案不存在: {file_location}"}, status_code=404)
    
    rag_status[filename] = False
    background_tasks.add_task(process_rag_with_thumbnails, file_location, output_subfolder, filename)
    
    logging.info(f"RAG 處理已啟動: {file_location}")
    return JSONResponse({
        "message": "RAG 處理已啟動",
        "thumbnails": []
    })

async def process_rag_with_thumbnails(file_location: str, output_folder: str, filename: str):
    try:
        thumbnails = []
        if Path(file_location).suffix.lower() == '.pdf':
            existing_thumbnails = get_existing_thumbnails(filename, output_folder)
            if existing_thumbnails:
                thumbnails = existing_thumbnails
            else:
                thumbnails = generate_pdf_thumbnails(file_location, output_folder)
        else:
            thumbnails = [f"/uploads/{filename}"]
        logging.info(f"截圖生成完成: {thumbnails}")

        #result = docling_extract_text_from_file(file_location, output_folder)
        result = extract_text_from_file(file_location, output_folder)
        if isinstance(result, list) and len(result) > 0 and result[0].startswith("錯誤:"):
            logging.error(f"RAG 處理失敗: {result[0]}")
            await manager.send_status(filename, False)  # 通知前端失敗
            return
        # 正常情況，result 是一個文字列表，處理成功
        logging.info(f"RAG 處理完成: {file_location}")
        rag_status[filename] = True
        await manager.send_status(filename, True)
    except Exception as e:
        logging.error(f"RAG 處理異常: {str(e)}", exc_info=True)
        rag_status[filename] = False
        await manager.send_status(filename, False)  # 通知前端失敗

@app.websocket("/ws/rag-status/{filename}")
async def websocket_rag_status(websocket: WebSocket, filename: str):
    await manager.connect(filename, websocket)
    try:
        while True:
            await asyncio.sleep(1)
            if filename in rag_status:
                await manager.send_status(filename, rag_status[filename])
                if rag_status[filename]:  # 僅在成功完成時斷開
                    break
    except WebSocketDisconnect:
        await manager.disconnect(filename)
    except Exception as e:
        logging.error(f"WebSocket 錯誤: {str(e)}")
        await websocket.send_json({"filename": filename, "is_complete": False, "error": str(e)})
    finally:
        await manager.disconnect(filename)

# LINE-BOT 路由
@app.post("/ask")
async def call_ask(request: Request):
    """處理 Line Bot 的問答請求。"""
    body = await request.body()
    signature = request.headers.get('X-Line-Signature', '')
    try:
        await handle_line_ask_message(body.decode('utf-8'), signature)
        logger.info(f"/ask 請求處理成功")
        return {"status": "ok"}
    except HTTPException as e:
        logger.error(f"/ask 請求發生 HTTP 錯誤: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"處理 /ask 路由時發生錯誤: {str(e)}", exc_info=True)  # 記錄完整堆棧
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e

@app.post("/assistant")
async def call_assistant(request: Request):
    """處理 Line Bot 的助理請求。"""
    body = await request.body()
    signature = request.headers.get('X-Line-Signature', '')
    try:
        await handle_line_assistant_message(body.decode('utf-8'), signature)
        logger.info(f"/assistant 請求處理成功")
        return {"status": "ok"}
    except HTTPException as e:
        logger.error(f"/assistant 請求發生 HTTP 錯誤: {str(e)}")
        raise e
    except Exception as e:
        logger.error(f"處理 /assistant 路由時發生錯誤: {str(e)}", exc_info=True)  # 記錄完整堆棧
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}") from e

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
