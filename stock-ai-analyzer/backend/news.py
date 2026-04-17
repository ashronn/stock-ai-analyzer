import feedparser
from datetime import datetime, timezone
import urllib.parse

def get_stock_news(ticker: str, company_name: str = "", max_news: int = 5) -> list:
    """ดึงข่าวหุ้นจาก Google News RSS"""

    query = f"{ticker} {company_name} stock".strip()
    encoded_query = urllib.parse.quote(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    try:
        feed = feedparser.parse(url)

        if not feed.entries:
            print(f"[NEWS] No entries found in feed for {ticker}")
            return []

        news_list = []

        for entry in feed.entries[:max_news * 2]:  # ดึงเผื่อไว้ก่อน filter
            # --- แปลงวันที่ (ไม่ตัดทิ้งถ้าแปลงไม่ได้) ---
            date_str = "ไม่ทราบวันที่"
            pub_date = None

            if hasattr(entry, "published_parsed") and entry.published_parsed:
                try:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    date_str = pub_date.strftime("%d/%m/%Y %H:%M")
                except Exception:
                    pass
            elif hasattr(entry, "published") and entry.published:
                date_str = entry.published  # ใช้ string เดิมถ้า parse ไม่ได้

            news_list.append({
                "title": entry.get("title", "ไม่มีหัวข้อ"),
                "link": entry.get("link", ""),
                "published": date_str,
                "source": entry.get("source", {}).get("title", "Unknown"),
                "pub_timestamp": pub_date.timestamp() if pub_date else 0,
            })

            if len(news_list) >= max_news:
                break

        # เรียงจากใหม่สุดก่อน (ถ้ามี timestamp)
        news_list.sort(key=lambda x: x["pub_timestamp"], reverse=True)

        # ลบ field ชั่วคราวออก
        for item in news_list:
            item.pop("pub_timestamp", None)

        print(f"[NEWS] Found {len(news_list)} articles for {ticker}")
        return news_list

    except Exception as e:
        print(f"[NEWS] Error fetching news for {ticker}: {e}")
        return []