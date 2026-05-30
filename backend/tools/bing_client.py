"""必应中文搜索客户端，参考 bing-cn-mcp-server 实现。"""

import re
import time
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

BING_SEARCH_URL = "https://cn.bing.com/search"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

CRAWLER_BLACKLIST = (
    "zhihu.com",
    "xiaohongshu.com",
    "xhs.com",
    "weibo.com",
    "weixin.qq.com",
    "mp.weixin.qq.com",
    "douyin.com",
    "tiktok.com",
    "bilibili.com",
    "csdn.net",
)

MAIN_CONTENT_SELECTORS = (
    "article",
    "main",
    '[role="main"]',
    ".article-content",
    ".post-content",
    ".content",
    ".main-content",
    "#content",
    "body",
)

MAX_PAGE_CONTENT_LEN = 2000
CRAWL_TOP_N = 2


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str
    display_url: str = ""
    page_content: str = ""


def is_url_blacklisted(url: str) -> bool:
    try:
        hostname = urlparse(url).hostname or ""
        hostname = hostname.lower()
        return any(
            hostname == domain or hostname.endswith(f".{domain}")
            for domain in CRAWLER_BLACKLIST
        )
    except Exception:
        return False


def fetch_bing_search_html(query: str, count: int = 10, offset: int = 0) -> str:
    params = {"q": query, "first": offset + 1, "setlang": "zh-Hans"}
    with httpx.Client(headers=DEFAULT_HEADERS, timeout=15.0, follow_redirects=True) as client:
        response = client.get(BING_SEARCH_URL, params=params)
        response.raise_for_status()
        return response.text


def parse_bing_search_results(html: str, query: str) -> list[SearchResult]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []

    for element in soup.select(".b_algo"):
        title_link = element.select_one("h2 a")
        if not title_link:
            continue

        title = title_link.get_text(strip=True)
        url = title_link.get("href", "").strip()
        if not title or not url:
            continue

        caption = element.select_one(".b_caption p")
        snippet = caption.get_text(strip=True) if caption else ""
        cite = element.select_one(".b_attribution cite")
        display_url = cite.get_text(strip=True) if cite else url

        results.append(
            SearchResult(
                title=title,
                url=url,
                snippet=snippet,
                display_url=display_url,
            )
        )

    if not results:
        raise RuntimeError(f"未能解析必应搜索结果，查询词：{query}")

    return results


def fetch_webpage_text(url: str) -> str:
    if is_url_blacklisted(url):
        raise RuntimeError(f"该网站在爬虫黑名单中，禁止抓取: {url}")

    with httpx.Client(headers=DEFAULT_HEADERS, timeout=30.0, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        html = response.text

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup.select("script, style, nav, footer, header, iframe, noscript"):
        tag.decompose()

    content = ""
    for selector in MAIN_CONTENT_SELECTORS:
        main = soup.select_one(selector)
        if main:
            content = main.get_text(separator="\n", strip=True)
            break

    content = re.sub(r"[ \t]+", " ", content)
    content = re.sub(r"\n{3,}", "\n\n", content).strip()

    if len(content) < 50:
        raise RuntimeError("提取的网页正文太少或为空")

    if len(content) > MAX_PAGE_CONTENT_LEN:
        content = content[:MAX_PAGE_CONTENT_LEN] + "…"

    return content


def search_with_content(
    query: str,
    max_results: int = 5,
    crawl_top_n: int = CRAWL_TOP_N,
) -> list[SearchResult]:
    last_error: Exception | None = None

    for attempt in range(2):
        try:
            if attempt > 0:
                time.sleep(1)
            html = fetch_bing_search_html(query, count=max_results)
            results = parse_bing_search_results(html, query)[:max_results]

            for i, result in enumerate(results[:crawl_top_n]):
                if is_url_blacklisted(result.url):
                    continue
                try:
                    if i > 0:
                        time.sleep(1)
                    result.page_content = fetch_webpage_text(result.url)
                except Exception:
                    continue

            return results
        except Exception as e:
            last_error = e

    if last_error:
        raise last_error
    return []
