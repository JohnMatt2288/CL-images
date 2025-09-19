# t66y_spider.py
import os
import sys
import requests
import logging
from bs4 import BeautifulSoup

# =================== 配置区 ====================
BASE_URL = "http://t66y.com"
IMAGE_DIR = "downloaded_images"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
# ================================================================

def get_thread_links(list_url):
    """抓取列表页，返回符合 [亞洲]/[亚洲] 的主题链接"""
    try:
        resp = requests.get(list_url, headers=HEADERS, timeout=15)
        resp.encoding = "gbk"
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.error(f"❌ 请求列表页失败: {e}")
        return []

    links = []
    for td in soup.find_all("td", class_="tal"):
        text = td.get_text(strip=True)
        if "[亚洲]" in text or "[亞洲]" in text:  # 支持简体/繁体
            a = td.find("a", href=True)
            if a:
                href = a["href"]
                if href.startswith("/"):
                    href = BASE_URL + href
                links.append(href)
                logger.info(f"🟢 发现主题: {href}")
    return links

def download_images_from_thread(url, save_root):
    """进入帖子下载图片"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = "gbk"
        soup = BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        logger.error(f"❌ 加载帖子失败 {url} - {e}")
        return

    # 获取帖子标题
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
    else:
        title = url.split("/")[-1]
    # 替换非法文件名字符
    title = title.replace("/", "_").replace("\\", "_").replace(":", "_")[:80]

    thread_dir = os.path.join(save_root, title)
    os.makedirs(thread_dir, exist_ok=True)

    img_tags = soup.find_all("img")
    count = 0
    for img in img_tags:
        src = img.get("data-link") or img.get("ess-data") or img.get("src")
        if not src:
            continue
        if src.startswith("/"):
            src = BASE_URL + src
        try:
            img_data = requests.get(src, headers=HEADERS, timeout=15).content
            ext = os.path.splitext(src)[1] or ".jpg"
            fname = os.path.join(thread_dir, f"{count:03d}{ext}")
            with open(fname, "wb") as f:
                f.write(img_data)
            count += 1
        except Exception as e:
            logger.warning(f"⚠️ 下载失败 {src} - {e}")

    if count > 0:
        logger.info(f"✅ 下载完成: {title} 共 {count} 张图片")
    else:
        logger.info(f"⚠️ {title} 没找到图片")

def main(start_page, end_page):
    os.makedirs(IMAGE_DIR, exist_ok=True)

    for page in range(start_page, end_page + 1):
        list_url = f"{BASE_URL}/thread0806.php?fid=8" if page == 1 else f"{BASE_URL}/thread0806.php?fid=8&search=&page={page}"
        logger.info(f"📄 抓取列表页: {list_url}")
        thread_links = get_thread_links(list_url)
        if not thread_links:
            logger.info("⚠️ 当前页没有符合条件的主题")
            continue

        for link in thread_links:
            download_images_from_thread(link, IMAGE_DIR)

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

    if start_page < 1 or start_page > end_page:
        print("❌ 页码范围不正确")
        sys.exit(1)

    main(start_page, end_page)
