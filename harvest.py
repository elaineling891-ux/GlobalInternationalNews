import requests
from bs4 import BeautifulSoup
from db import insert_news, news_exists
import time
from urllib.parse import urljoin
from deep_translator import GoogleTranslator

# --------------------------
# 初始化 Cohere 改写 API
# --------------------------
COHERE_API_KEY = "W2pkO3EABJq0LyPyCZ6I1yYwBsLuuiiHDG45qmO5"
COHERE_URL = "https://api.cohere.ai/v1/chat"

def rewrite_text_cohere(text: str) -> str:
    headers = {
        "Authorization": f"Bearer {COHERE_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "command-r",  # ✅ 最新模型
        "message": f"请用中文改写以下文本，保持原意但用不同的措辞：\n\n{text}",
        "temperature": 0.7
    }

    resp = requests.post(COHERE_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        print("Cohere 改写失败:", resp.status_code, resp.text)
        return text

    data = resp.json()
    try:
        return data["text"]  # chat 接口会直接给一个 text 字段
    except KeyError:
        return text

# --------------------------
# 后处理：添加换行，每3句换一次行
# --------------------------
def add_linebreaks(text, n_sentences=3):
    import re
    sentences = re.split(r'(?<=[。！？.!?])', text)
    lines = []
    for i in range(0, len(sentences), n_sentences):
        lines.append("".join(sentences[i:i+n_sentences]))
    return "\n\n".join(lines)

# --------------------------
# 翻译成简体中文
# --------------------------
def translate_to_simplified(text: str) -> str:
    try:
        return GoogleTranslator(source="auto", target="zh-CN").translate(text)
    except Exception as e:
        print("翻译失败:", e)
        return text

def rewrite_text(text):
    rewritten = rewrite_text_cohere(text)
    rewritten = add_linebreaks(rewritten)
    return translate_to_simplified(rewritten)  # ✅ 最后翻译成简体

# --------------------------
# 以下抓取文章内容、图片、网站新闻等保持不变
# --------------------------
def fetch_article_content(link):
    if not link:
        return ""
    try:
        resp = requests.get(link, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        if "udn.com" in link:
            div = soup.select_one("div#story_body_content")
        elif "ltn.com" in link:
            div = soup.select_one("div.text")
        elif "yahoo.com" in link:
            div = soup.select_one("article")
        else:
            div = None

        if div:
            paragraphs = div.find_all("p")
            content = "\n".join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            return content
    except Exception as e:
        print(f"抓文章内容失败 ({link}): {e}")
    return ""

def fetch_article_image(link):
    if not link:
        return None
    try:
        resp = requests.get(link, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")
        img_url = None

        if "udn.com" in link:
            div = soup.select_one("div#story_body_content")
            if div:
                img = div.find("img")
                if img:
                    img_url = img.get("data-src") or img.get("src")
        elif "ltn.com" in link:
            div = soup.select_one("div.text")
            if div:
                img = div.find("img")
                if img:
                    img_url = img.get("src")
        elif "yahoo.com" in link:
            meta = soup.select_one('meta[property="og:image"]')
            if meta:
                img_url = meta.get("content")

        if img_url and img_url.startswith("/"):
            img_url = urljoin(link, img_url)

        return img_url
    except Exception as e:
        print(f"抓文章图片失败 ({link}): {e}")
    return None

def fetch_site_news(url, limit=20):
    news_items = []
    try:
        resp = requests.get(url, timeout=20)
        soup = BeautifulSoup(resp.text, "html.parser")

        if "udn.com" in url:
            items = soup.select("div.story-list__text a")
        elif "ltn.com" in url:
            items = soup.select("div.title a")
        elif "yahoo.com" in url:
            # Yahoo 首页不一定固定 h3 a，用 a[href*="/news/"] 更稳
            items = soup.select("a[href*='/news/']")
        else:
            items = []

        for item in items[:limit]:
            title = item.get_text(strip=True)
            link = item.get("href")
            if link and link.startswith("/"):
                link = urljoin(url, link)

            # 针对 Yahoo：强制进入详情页抓真正标题
            if "yahoo.com" in url and link and link.startswith("http"):
    try:
        article_res = requests.get(link, timeout=10)
        article_soup = BeautifulSoup(article_res.text, "html.parser")

        # 1. 先抓 h1
        h1 = article_soup.select_one("h1")
        if h1:
            title = h1.get_text(strip=True)
        else:
            # 2. 再退到 og:title
            og_title = article_soup.select_one("meta[property='og:title']")
            if og_title and og_title.get("content"):
                title = og_title["content"].strip()
            # 3. 最后兜底 <title>
            elif article_soup.title:
                title = article_soup.title.string.strip()

    except Exception as e:
        print(f"Yahoo 抓文章标题失败: {e}")

            news_items.append((title, link))

    except Exception as e:
        print(f"抓 {url} 出错: {e}")
    return news_items

def fetch_news():
    all_news = []
    sites = [
        "https://udn.com/news/index",
        "https://www.ltn.com.tw",
        "https://tw.news.yahoo.com/"
    ]

    for url in sites:
        for title, link in fetch_site_news(url, limit=20):
            if not link or news_exists(link):
                continue
            content = fetch_article_content(link)
            if not content:
                continue
            image_url = fetch_article_image(link)
            title_rw = rewrite_text(title)
            content_rw = rewrite_text(content)
            try:
                insert_news(title_rw, content_rw, link, image_url)
                all_news.append({
                    "title": title_rw,
                    "content": content_rw,
                    "link": link,
                    "image_url": image_url
                })
                print(f"✅ 改写成功并保存: {title_rw[:30]}...")
            except Exception as e:
                print(f"插入失败: {e}")
