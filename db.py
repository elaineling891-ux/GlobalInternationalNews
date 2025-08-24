import psycopg2
import os
import sqlite3

DB_URL = os.getenv("DATABASE_URL")

def init_db():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS news (
        id SERIAL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT,
        link TEXT,
        image_url TEXT,
        -- 存本地时间（新加坡），无时区
        created_at TIMESTAMP DEFAULT (NOW() AT TIME ZONE 'Asia/Singapore'),
        UNIQUE(title),
        UNIQUE(link)
    )
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ 数据库初始化完成（created_at=SGT）")

def insert_news(title, content, link=None, image_url=None):
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO news (title, content, link, image_url)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (link) DO NOTHING
    """, (title, content, link, image_url))
    conn.commit()
    cur.close()
    conn.close()

def get_news(limit=20, offset=0):
    conn = psycopg2.connect(DB_URL)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, title, url, content, image_url, source, created_at
        FROM news
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    rows = cursor.fetchall()
    conn.close()

    # 转换成字典方便前端用
    return [
        {
            "id": r[0],
            "title": r[1],
            "url": r[2],
            "content": r[3],
            "image_url": r[4],
            "source": r[5],
            "created_at": r[6],
        }
        for r in rows
    ]

def get_all_news(skip=0, limit=20):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM news ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (limit, skip)
    )
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def news_exists(link: str) -> bool:
    """检查数据库里是否已经有这个链接"""
    if not link:
        return False
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM news WHERE link=%s LIMIT 1", (link,))
    exists = cur.fetchone() is not None
    cur.close()
    conn.close()
    return exists
