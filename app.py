import asyncio
import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from db import get_all_news, init_db,get_news_by_id
from harvest import fetch_news
from datetime import datetime
import requests

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# --------------------------
# 启动事件：初始化 DB + 异步定时抓新闻
# --------------------------
@app.on_event("startup")
async def startup_event():
    init_db()  # 初始化数据库表
    asyncio.create_task(periodic_fetch_news(43200))  # 每 30 分钟抓一次新闻
    asyncio.create_task(keep_alive_task("https://your-app.onrender.com/"))

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

async def keep_alive_task(url, interval=300):
    while True:
        try:
            r = requests.get(url, timeout=10)
            print(f"[keep-alive] {r.status_code}")
        except Exception as e:
            print("[keep-alive] 请求失败:", e)
        await asyncio.sleep(interval)

# --------------------------
# Uvicorn 入口
# --------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=True)
