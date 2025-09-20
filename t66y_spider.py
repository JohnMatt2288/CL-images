import os
import sys
import time
import logging
import requests
import shutil
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

# ================== 配置 ==================
BASE_URL = "https://t66y.com/thread0806.php?fid=8&type=1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0 Safari/537.36"
}
OUTPUT_DIR = "downloaded_images"

# ================== 日志 ==================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def fetch(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = "utf-8"
        if resp.status_code == 200:
            return resp.text
        logger.warning(f"请求失败 {resp.status_code}: {url}")
        return None
    except Exception as e:
        logger.error(f"请求异常 {url}: {e}")
        return None


def parse_list_page(html):
    soup = BeautifulSoup(html, "html.parser")
    tbody = soup.find("tbody", id="tbody")
    if not tbody:
        return []

    results = []
    for tr in tbody.find_all("tr", class_="tr3 t_one tac"):
        h3 = tr.find("h3")
        if not h3:
            continue
        a = h3.find("a")
        if not a:
            continue
        title = a.get_text(strip=True).replace("/", "_").replace("\\", "_")
        href = a.get("href")
        if not href:
            continue
        full_url = urljoin("https://t66y.com/", href)
        results.append((title, full_url))
    return results


def parse_detail_page(html):
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", id="conttpc")
    if not content:
        return []

    img_urls = []
    for img_tag in content.find_all("img"):
        url = img_tag.get("ess-data") or img_tag.get("src")
        if url and url.startswith("http"):
            img_urls.append(url)
    return img_urls


def download_image(img_url, folder, index):
    try:
        resp = requests.get(img_url, headers=HEADERS, stream=True, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"下载失败 {resp.status_code}: {img_url}")
            return False

        parsed = urlparse(img_url)
        ext = os.path.splitext(parsed.path)[1]
        if not ext or len(ext) > 5:
            ext = ".jpg"

        filename = f"{index:03d}{ext}"
        filepath = os.path.join(folder, filename)

        with open(filepath, "wb") as f:
            for chunk in resp.iter_content(1024):
                f.write(chunk)

        logger.info(f"下载成功: {filename}")
        return True
    except Exception as e:
        logger.error(f"下载异常 {img_url}: {e}")
        return False


def crawl_detail(title, url):
    html = fetch(url)
    if not html:
        return

    img_urls = parse_detail_page(html)
    if not img_urls:
        logger.info(f"无图片: {title}")
        return

    folder = os.path.join(OUTPUT_DIR, title[:100])
    os.makedirs(folder, exist_ok=True)

    for idx, img_url in enumerate(img_urls, 1):
        download_image(img_url, folder, idx)

    logger.info(f"完成主题: {title} - {len(img_urls)} 张图片")


def main(start_page, end_page):
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for page in range(start_page, end_page + 1):
        url = f"{BASE_URL}&page={page}"
        logger.info(f"抓取列表页: {url}")
        html = fetch(url)
        if not html:
            continue

        topics = parse_list_page(html)
        if not topics:
            logger.info("⚠️ 当前页没有主题")
            continue

        for title, link in topics:
            logger.info(f"进入主题: {title} -> {link}")
            crawl_detail(title, link)
            time.sleep(2)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"用法: python {sys.argv[0]} <start_page> <end_page>")
        sys.exit(1)

    start_page = int(sys.argv[1])
    end_page = int(sys.argv[2])
    main(start_page, end_page)

    # === 🔽 打包目录为 zip ===
    zip_file = shutil.make_archive("downloaded_images", "zip", OUTPUT_DIR)
    logger.info(f"📦 打包完成: {zip_file}")

    logger.info("🔚 所有任务完成")
