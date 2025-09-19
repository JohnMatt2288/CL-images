import os
import re
import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import sys

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

BASE_URL = "http://t66y.com"
LIST_URL = "https://t66y.com/thread0806.php?fid=8&type=1&page={page}"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

SAVE_DIR = "downloads"
os.makedirs(SAVE_DIR, exist_ok=True)

def fetch_page(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.encoding = "utf-8"
        return resp.text
    except Exception as e:
        logging.error(f"请求失败 {url}: {e}")
        return None

def parse_list_page(html):
    """解析列表页，返回 (标题, 链接) 列表"""
    soup = BeautifulSoup(html, "lxml")
    tbody = soup.find("tbody", id="tbody")
    results = []
    if not tbody:
        logging.warning("⚠️ 未找到 tbody")
        return results
    rows = tbody.find_all("tr", class_="tr3 t_one tac")
    for row in rows:
        a_tag = row.find("h3").find("a") if row.find("h3") else None
        if not a_tag:
            continue
        title = a_tag.get_text(strip=True)
        href = urljoin(BASE_URL, a_tag["href"])
        results.append((title, href))
    return results

def parse_thread_page(html):
    """解析主题页，返回所有图片链接"""
    soup = BeautifulSoup(html, "lxml")
    img_tags = soup.find_all("input", src=True) + soup.find_all("img", src=True)
    urls = []
    for tag in img_tags:
        src = tag["src"]
        if src.lower().endswith((".jpg", ".jpeg", ".png")):
            urls.append(src)
    return urls

def download_image(url, folder, idx):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        if resp.status_code == 200:
            ext = os.path.splitext(url)[-1].split("?")[0]
            if ext.lower() not in [".jpg", ".jpeg", ".png"]:
                ext = ".jpg"
            filename = os.path.join(folder, f"{idx}{ext}")
            with open(filename, "wb") as f:
                f.write(resp.content)
            logging.info(f"✅ 下载成功: {filename}")
    except Exception as e:
        logging.error(f"下载失败 {url}: {e}")

def main(start_page, end_page):
    for page in range(start_page, end_page + 1):
        url = LIST_URL.format(page=page)
        logging.info(f"📄 抓取列表页: {url}")
        html = fetch_page(url)
        if not html:
            continue
        threads = parse_list_page(html)
        logging.info(f"第 {page} 页共找到 {len(threads)} 个主题")

        for title, link in threads:
            logging.info(f"➡️ 进入主题: {title} ({link})")
            html = fetch_page(link)
            if not html:
                continue
            img_urls = parse_thread_page(html)
            if not img_urls:
                logging.info("⚠️ 未找到图片")
                continue
            # 建立文件夹保存
            safe_title = re.sub(r'[\\/*?:"<>|]', "_", title)
            folder = os.path.join(SAVE_DIR, safe_title)
            os.makedirs(folder, exist_ok=True)
            # 下载图片
            for idx, img_url in enumerate(img_urls, 1):
                download_image(img_url, folder, idx)
            time.sleep(1)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"用法: python {sys.argv[0]} <start_page> <end_page>")
        sys.exit(1)
    start = int(sys.argv[1])
    end = int(sys.argv[2])
    main(start, end)
