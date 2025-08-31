from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime

from db import (
    init_db, get_all_news, get_news_by_id, insert_news,
    update_news, delete_news,
    get_news_by_category, get_news_grouped_by_category
)

app = FastAPI()

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup_event():
    init_db()


# 首页
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    category_news = get_news_grouped_by_category(limit=5)
    return templates.TemplateResponse("main.html", {
        "request": request,
        "category_news": category_news,
        "year": datetime.now().year
    })


# 分类页
@app.get("/category/{category}", response_class=HTMLResponse)
async def category_page(request: Request, category: str):
    news_list = get_news_by_category(category, limit=20)
    return templates.TemplateResponse("category.html", {
        "request": request,
        "category": category,
        "news_list": news_list,
        "year": datetime.now().year
    })


# 详情页
@app.get("/news/{news_id}", response_class=HTMLResponse)
async def news_detail(request: Request, news_id: int):
    news = get_news_by_id(news_id)
    if not news:
        return HTMLResponse(content="News not found", status_code=404)
    return templates.TemplateResponse("news_detail.html", {
        "request": request,
        "news": news,
        "year": datetime.now().year
    })


# ===== Admin 页面 =====

# 后台管理首页（显示所有新闻 + 管理按钮）
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    news_list = get_all_news()
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "news_list": news_list
    })


# 新增新闻页面
@app.get("/admin/add", response_class=HTMLResponse)
async def add_news_form(request: Request):
    return templates.TemplateResponse("admin_add.html", {"request": request})


# 新增新闻提交
@app.post("/admin/add")
async def add_news(
    title: str = Form(...),
    content: str = Form(...),
    link: str = Form(None),
    image_url: str = Form(None),
    category: str = Form(None)
):
    insert_news(title, content, link, image_url, category)
    return RedirectResponse(url="/admin", status_code=303)


# 编辑新闻页面
@app.get("/admin/edit/{news_id}", response_class=HTMLResponse)
async def edit_news_form(request: Request, news_id: int):
    news = get_news_by_id(news_id)
    if not news:
        return HTMLResponse(content="News not found", status_code=404)
    return templates.TemplateResponse("admin_edit.html", {
        "request": request,
        "news": news
    })


# 提交修改
@app.post("/admin/update/{news_id}")
async def edit_news(
    news_id: int,
    title: str = Form(...),
    content: str = Form(...),
    link: str = Form(None),
    image_url: str = Form(None),
    category: str = Form(None)
):
    update_news(news_id, title, content, link, image_url, category)
    return RedirectResponse(url="/admin", status_code=303)


# 删除新闻
@app.get("/admin/delete/{news_id}")
async def remove_news(news_id: int):
    delete_news(news_id)
    return RedirectResponse(url="/admin", status_code=303)
