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
        "model": "command-r",
        "message": f"请用中文改写以下文本，保持原意但用不同的措辞：\n\n{text}",
        "temperature": 0.7
    }

    resp = requests.post(COHERE_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        print("Cohere 改写失败:", resp.status_code, resp.text)
        return text

    data = resp.json()
    try:
        return data["text"]
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
    return translate_to_simplified(rewritten)

# --------------------------
# 抓取文章内容
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

# --------------------------
# 抓取文章图片
# --------------------------
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

# --------------------------
# 抓取网站新闻列表
# --------------------------
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
            # ✅ 修正 Yahoo 的 title 抓取
            items = soup.select("h3 a span") or soup.select("a[aria-label]")
        else:
            items = []

        for item in items[:limit]:
            if item.name == "span":
                title = item.get_text(strip=True)
                link = item.parent.get("href")
            else:
                title = item.get_text(strip=True)
                link = item.get("href")

            if link and link.startswith("/"):
                link = urljoin(url, link)

            if title and link:
                news_items.append((title, link))
    except Exception as e:
        print(f"抓 {url} 出错: {e}")
    return news_items

# --------------------------
# 主抓取流程
# --------------------------
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
    return all_news
