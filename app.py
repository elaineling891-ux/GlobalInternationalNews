from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from datetime import datetime

from db import (
    init_db, get_all_news, get_news_by_id, insert_news,
    update_news, delete_news,
    get_news_by_category, get_news_grouped_by_category,
    get_all_categories
)

app = FastAPI()

# 静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

# 模板路径
templates = Jinja2Templates(directory="templates")


@app.on_event("startup")
def startup_event():
    init_db()


# -------------------- 前台页面 --------------------

# 首页
@app.get("/", response_class=HTMLResponse)
async def main(request: Request):
    category_news = get_news_grouped_by_category(limit=5)
    return templates.TemplateResponse("main.html", {
        "request": request,
        "category_news": category_news,
        "year": datetime.now().year
    })


# 分类页
@app.get("/category/{category}", response_class=HTMLResponse)
async def category_page(request: Request, category: str, page: int = 1, per_page: int = 20):
    offset = (page - 1) * per_page
    news_list = get_news_by_category(category, limit=per_page, offset=offset)
    categories = get_all_categories()
    return templates.TemplateResponse("category.html", {
        "request": request,
        "category": category,
        "news_list": news_list,
        "categories": categories,
        "year": datetime.now().year,
        "current_page": page,
        "per_page": per_page
    })



# 新闻详情页
@app.get("/news/{news_id}", response_class=HTMLResponse)
async def news_detail(request: Request, news_id: int):
    news = get_news_by_id(news_id)
    if not news:
        return HTMLResponse(content="News not found", status_code=404)
    categories = get_all_categories()
    return templates.TemplateResponse("news_detail.html", {
        "request": request,
        "news": news,
        "categories": categories,
        "year": datetime.now().year
    })


# 关于我们
@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    categories = get_all_categories()
    return templates.TemplateResponse("about.html", {"request": request, "categories": categories, "year": datetime.now().year})


# 联系我们
@app.get("/contact", response_class=HTMLResponse)
async def contact(request: Request):
    categories = get_all_categories()
    return templates.TemplateResponse("contact.html", {"request": request, "categories": categories, "year": datetime.now().year})


# 隐私政策
@app.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    categories = get_all_categories()
    return templates.TemplateResponse("privacy.html", {"request": request, "categories": categories, "year": datetime.now().year})


# 使用条款
@app.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    categories = get_all_categories()
    return templates.TemplateResponse("terms.html", {"request": request, "categories": categories, "year": datetime.now().year})


# 免责声明
@app.get("/disclaimer", response_class=HTMLResponse)
async def disclaimer(request: Request):
    categories = get_all_categories()
    return templates.TemplateResponse("disclaimer.html", {"request": request, "categories": categories, "year": datetime.now().year})


# -------------------- 后台管理 --------------------

# 后台首页（新闻列表）
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    news_list = get_all_news()
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request,
        "news_list": news_list,
        "year": datetime.now().year
    })


# 新增新闻页面
@app.get("/admin/add", response_class=HTMLResponse)
async def admin_add_page(request: Request):
    categories = get_all_categories()
    return templates.TemplateResponse("admin_add.html", {
        "request": request,
        "categories": categories,
        "year": datetime.now().year
    })


# 提交新增新闻
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
async def admin_edit_page(request: Request, news_id: int):
    news = get_news_by_id(news_id)
    categories = get_all_categories()
    if not news:
        return HTMLResponse(content="News not found", status_code=404)
    return templates.TemplateResponse("admin_edit.html", {
        "request": request,
        "news": news,
        "categories": categories,
        "year": datetime.now().year
    })


# 提交更新新闻
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
