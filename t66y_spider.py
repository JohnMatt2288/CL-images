# t66y_spider.py
import os
import sys
import time
import requests
import logging
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# =================== 配置区 ====================
BASE_URL = "https://t66y.com/thread0806.php?fid=8"
IMAGE_DIR = "downloaded_images"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# ================================================================

def fetch_page(page_num: int):
    """抓取列表页 HTML"""
    url = BASE_URL if page_num == 1 else f"{BASE_URL}&search=&page={page_num}"
    logger.info(f"📄 抓取列表页: {url}")
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = "utf-8"
        return resp.text
    except Exception as e:
        logger.error(f"❌ 请求失败: {e}")
        return None

def parse_topics(html: str):
    """解析页面，提取带 [亚洲] 的主题链接"""
    soup = BeautifulSoup(html, "html.parser")
    topics = []
    for td in soup.find_all("td", class_="tal"):
        if "[亚洲]" not in td.get_text(strip=True):
            continue
        a_tag = td.find("a", href=True)
        if not a_tag:
            continue
        link = urljoin(BASE_URL, a_tag["href"])
        title = a_tag.get_text(strip=True).replace("/", "_").replace("\\", "_")[:80]
        topics.append((title, link))
        logger.info(f"🟢 发现 [亚洲] 主题: {title} -> {link}")
    return topics

def parse_images(topic_url: str):
    """进入帖子页面，提取图片 URL"""
    try:
        resp = requests.get(topic_url, headers=HEADERS, timeout=15)
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logger.error(f"❌ 加载帖子失败: {e}")
        return []

    content_div = soup.find("div", id="conttpc") or soup.find("div", class_="tpc_content do_not_catch")
    if not content_div:
        logger.warning("⚠️ 未找到内容区域")
        return []

    img_urls = []
    for img in content_div.find_all("img"):
        url = img.get("data-link") or img.get("ess-data") or img.get("src")
        if url:
            img_urls.append(url.strip())
    logger.info(f"📷 找到 {len(img_urls)} 张图片")
    return img_urls

def download_image(img_url, folder_path, index):
    """下载图片"""
    try:
        resp = requests.get(img_url, headers=HEADERS, stream=True, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"⚠️ 下载失败: {img_url}")
            return False
        ext = os.path.splitext(urlparse(img_url).path)[1] or ".jpg"
        filename = f"{index:03d}{ext}"
        filepath = os.path.join(folder_path, filename)
        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(1024):
                f.write(chunk)
        logger.info(f"✅ 已下载: {filename}")
        return True
    except Exception as e:
        logger.error(f"❌ 下载异常: {e}")
        return False

def process_topic(title, link):
    """处理单个主题：下载所有图片"""
    folder_path = os.path.join(IMAGE_DIR, title)
    os.makedirs(folder_path, exist_ok=True)
    img_urls = parse_images(link)
    if not img_urls:
        return
    for idx, img_url in enumerate(img_urls, 1):
        download_image(img_url, folder_path, idx)

def main(start, end):
    os.makedirs(IMAGE_DIR, exist_ok=True)

    for page in range(start, end + 1):
        html = fetch_page(page)
        if not html:
            continue
        topics = parse_topics(html)
        for title, link in topics:
            process_topic(title, link)

    logger.info("🔚 所有任务完成")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python t66y_spider.py <起始页码> <结束页码>")
        sys.exit(1)

    try:
        start_page = int(sys.argv[1])
        end_page = int(sys.argv[2])
    except ValueError:
        print("❌ 页码必须是整数")
        sys.exit(1)

    if start_page > end_page or start_page < 1:
        print("❌ 页码范围不正确")
        sys.exit(1)

    main(start_page, end_page)
