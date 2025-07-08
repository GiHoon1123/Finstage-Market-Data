import requests
import hashlib
from bs4 import BeautifulSoup
from app.news_crawler.service.dc_news_processor import  DcNewsProcessor

class DcUsStockGalleryCrawler:
    def __init__(self, gallery_id="stockus", page=1):
        self.gallery_id = gallery_id
        self.page = page
        self.base_url = "https://gall.dcinside.com/mgallery/board/lists"

    def crawl(self):
        params = {"id": self.gallery_id, "page": self.page}
        headers = {"User-Agent": "Mozilla/5.0"}

        res = requests.get(self.base_url, params=params, headers=headers)
        if res.status_code != 200:
            print(f"❌ 요청 실패: {res.status_code}")
            return []

        soup = BeautifulSoup(res.text, "html.parser")
        rows = soup.select("tr.us-post:not(.notice), tr.ub-content")
        if not rows:
            print("❗ 게시글을 찾을 수 없습니다. HTML 구조가 바뀌었을 수 있습니다.")
            return []

        posts = []
        for row in rows:
            title_tag = row.select_one("td.gall_tit a")
            if not title_tag:
                continue

            title = title_tag.text.strip()
            url = "https://gall.dcinside.com" + title_tag["href"]
            author = row.select_one("span.nickname") or row.select_one("td.gall_writer")
            author_name = author.text.strip() if author else "익명"
            date = row.select_one("td.gall_date").get("title") or row.select_one("td.gall_date").text.strip()

            posts.append({
                "title": title,
                "url": url,
                "summary": None,  # DC 글은 요약 없음
                "author": author_name,
                "published_at": date,
                "source": "dcinside.com",
                "symbol": "DC_US",  
                "content_hash": hashlib.sha256(title.encode("utf-8")).hexdigest(),
                "html": "",
            })

        return posts


if __name__ == "__main__":
    crawler = DcUsStockGalleryCrawler(page=1)
    posts = crawler.crawl()

    if posts:
        processor = DcNewsProcessor(posts)
        processor.run()
