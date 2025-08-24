import psycopg2
import os

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


def get_all_news(skip=0, limit=20):
    conn = psycopg2.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
   cursor.execute("""
    SELECT id, title, content, link, image_url, created_at
    FROM news
    ORDER BY created_at DESC
    LIMIT %s OFFSET %s
""", (limit, offset))
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
