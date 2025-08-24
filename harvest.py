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
