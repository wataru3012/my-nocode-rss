import os
import json
import cloudscraper
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

# 1. 設定ファイルの読み込み
with open('config.json', 'r', encoding='utf-8') as f:
    sites = json.load(f)

# ボットフィルターを自動で回避する既製品のスクレイパーを初期化
scraper = cloudscraper.create_scraper()

for site in sites:
    print(f"Generating: {site['title']}")
    
    try:
        # タイムアウトを防ぎ、ブラウザの挙動を完璧に模倣してHTMLを取得
        response = scraper.get(site['url'], timeout=15)
        html = response.text
    except Exception as e:
        print(f"  [Skip] アクセス失敗: {e}")
        continue

    soup = BeautifulSoup(html, 'html.parser')
    fg = FeedGenerator()
    fg.id(site['url'])
    fg.title(site['title'])
    fg.link(href=site['url'], rel='alternate')
    fg.description(site['title'])

    # 各要素を抽出
    for item in soup.select(site['item_selector'])[:100]:
        t_el = item.select_one(site['title_selector'])
        l_el = item.select_one(site['link_selector'])
        if t_el and l_el and l_el.get('href'):
            fe = fg.add_entry()
            fe.id(l_el.get('href'))
            fe.title(t_el.get_text(strip=True))
            fe.link(href=l_el.get('href'))

    os.makedirs('public', exist_ok=True)
    fg.rss_file(f"public/{site['filename']}", pretty=True)
    print(f"  [Success] Saved to public/{site['filename']}")
