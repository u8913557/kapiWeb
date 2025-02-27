# main.py
import os
from fastapi import FastAPI, Request, Header, HTTPException
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
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

from utils.llm_utils import create_plain_llm

# 延遲載入 LLM
llm_chain = None

def get_llm_chain():
    global llm_chain
    if llm_chain is None:
        llm_chain = create_plain_llm()
    return llm_chain

# 首页路由
@app.get("/", response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/chat-submit")
async def submit_chat(request: Request):
    form_data = await request.form()
    text = form_data.get('text')

    llm_chain = get_llm_chain()
    response = llm_chain.invoke(text)

    return JSONResponse(content={"result": f"AI回答:\n{response}"})

# LINE-BOT路由

from utils.line_bot_handler import handle_line_ask_message, handle_line_assistant_message

@app.post("/ask")
async def call_ask(request: Request, x_line_signature: str = Header(None)):
    signature = x_line_signature
    body = await request.body()
    body_str = body.decode('utf-8')
    print("Request body:", body_str)

    try:
        llm_chain = get_llm_chain()
        handle_line_ask_message(body_str, signature, llm_chain)
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
        llm_chain = get_llm_chain()
        handle_line_assistant_message(body_str, signature, llm_chain)
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Error handling Line assistant message: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

    return "OK"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
