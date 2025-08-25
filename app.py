import asyncio
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from db import get_all_news, init_db,get_news_by_id
from harvest import fetch_news
from datetime import datetime
import requests
import time

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --------------------------
# 启动事件：初始化 DB + 异步定时抓新闻
# --------------------------
@app.on_event("startup")
async def startup_event():
    init_db()  # 初始化数据库表
    asyncio.create_task(periodic_fetch_news(43200))  # 每 30 分钟抓一次新闻
    asyncio.create_task(periodic_keep_alive(300))

async def periodic_fetch_news(interval=43200):
    while True:
        try:
            print(f"⏳ [{datetime.now()}] 开始抓新闻...")
            await asyncio.get_event_loop().run_in_executor(None, fetch_news)
            print(f"✅ [{datetime.now()}] 抓新闻完成")
        except Exception as e:
            print("抓新闻出错:", e)
        await asyncio.sleep(interval)

# --------------------------
# 首页
# --------------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    news = get_all_news()  # 从数据库获取新闻
    return templates.TemplateResponse("index.html", {
        "request": request,
        "news": news,
        "year": datetime.now().year
    })

# --------------------------
# 新闻详情页，根据数据库 id
# --------------------------
@app.get("/news/{news_id}", response_class=HTMLResponse)
async def news_detail(request: Request, news_id: int):
    news_item = get_news_by_id(news_id)
    if not news_item:
        return HTMLResponse(content="新闻不存在", status_code=404)
    return templates.TemplateResponse("detail.html", {
        "request": request,
        "news_item": news_item,
        "year": datetime.now().year
    })

@app.get("/api/news", response_class=JSONResponse)
async def api_news(skip: int = 0, limit: int = 20):
    news = get_all_news(skip=skip, limit=limit)
    return {"news": news}
# --------------------------
# 测试数据库连接
# --------------------------
@app.get("/check_db")
async def check_db():
    try:
        news = get_all_news()
        return {"tables_exist": True, "news_count": len(news)}
    except Exception as e:
        return {"tables_exist": False, "error": str(e)}

# --------------------------
# 手动抓新闻接口
# --------------------------
@app.api_route("/manual_fetch", methods=["GET", "POST"])
async def manual_fetch():
    try:
        new_news = await asyncio.get_event_loop().run_in_executor(None, fetch_news)
        return {"status": "success", "fetched_count": len(new_news)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    return templates.TemplateResponse("contact.html", {"request": request})

@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})

@app.get("/ads.txt", response_class=PlainTextResponse)
async def ads_txt():
    return "google.com, pub-2460023182833054, DIRECT, f08c47fec0942fa0"

KEEP_ALIVE_URLS = [
    "https://globalnews-5ose.onrender.com/"
]

async def periodic_keep_alive(interval=300, retry_delay=60):
    """异步后台 keep-alive 任务"""
    while True:
        for url in KEEP_ALIVE_URLS:
            success = False
            attempts = 0
            while not success:
                try:
                    attempts += 1
                    # 用 run_in_executor 保持非阻塞
                    await asyncio.get_event_loop().run_in_executor(
                        None, lambda: requests.get(url, timeout=60)
                    )
                    print(f"[{datetime.now()}] keep-alive 成功: {url}")
                    success = True
                except Exception as e:
                    print(f"[{datetime.now()}] keep-alive 失败 (尝试 {attempts}): {url} 错误: {e}")
                    await asyncio.sleep(retry_delay)  # 失败重试等待 1 分钟
        await asyncio.sleep(interval)  # 主循环间隔，默认 5 分钟

# --------------------------
# Uvicorn 入口
# --------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
