import os
import json
import time  # ⏳ 429対策のウェイト用に追加
import cloudscraper
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

with open('config.json', 'r', encoding='utf-8') as f:
    sites = json.load(f)

scraper = cloudscraper.create_scraper()

for site in sites:
    max_pages = site.get('pages', 1)
    print(f"Generating: {site['title']} (Target: {max_pages} pages)")
    
    fg = FeedGenerator()
    fg.id(site['url'])
    fg.title(site['title'])
    fg.link(href=site['url'], rel='alternate')
    fg.description(site['title'])
    
    added_links = set()

    for page_num in range(1, max_pages + 1):
        target_url = site['url']
        
        if page_num > 1:
            # 💡 404対策：WordPressなどの「/page/2/」形式か、通常の「?page=2」形式かを自動判定
            if "hatenablog" in site['url'] or "impress" in site['url']:
                join_char = '&' if '?' in site['url'] else '?'
                target_url = f"{site['url']}{join_char}page={page_num}&p={page_num}"
            else:
                # 末尾のスラッシュを考慮して /page/2/ の形を作る（WordPress標準）
                base_url = site['url'].rstrip('/')
                target_url = f"{base_url}/page/{page_num}/"
                
            print(f"  -> Fetching Page {page_num}: {target_url}")

        try:
            # ⏳ 429対策：連続アクセスを避けるため、2ページ目以降は1.5秒待つ
            if page_num > 1:
                time.sleep(3.0)

            response = scraper.get(target_url, timeout=15)
            
            if response.status_code != 200:
                print(f"   [Page End] ステータスコード: {response.status_code}")
                break
            html = response.text
        except Exception as e:
            print(f"   [Page Skip] アクセス失敗: {e}")
            break

        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select(site['item_selector'])
        
        # 💡 デバッグ用：もし1件も取れなかったら、何が起きているかログを出す
        if page_num == 1 and not items:
            print(f"   ⚠️ [Debug] 1ページ目のパースに失敗。HTMLの文字数: {len(html)}")
            if "Cloudflare" in html or "Just a moment" in html:
                print("   -> 原因: Cloudflareの強固なボットフィルターにブロックされています。")

        if not items:
            break

        for item in items[:100]:
            t_el = item.select_one(site['title_selector'])
            l_el = item.select_one(site['link_selector'])
            
            if t_el and l_el and l_el.get('href'):
                link_url = l_el.get('href')
                
                # 相対パス（/entry/xxxなど）だった場合に絶対パスに補完
                if link_url.startswith('/'):
                    from urllib.parse import urljoin
                    link_url = urljoin(site['url'], link_url)

                if link_url in added_links:
                    continue
                
                fe = fg.add_entry()
                fe.id(link_url)
                fe.title(t_el.get_text(strip=True))
                fe.link(href=link_url)
                added_links.add(link_url)

    if added_links:
        os.makedirs('public', exist_ok=True)
        fg.rss_file(f"public/{site['filename']}", pretty=True)
        print(f"  [Success] Saved {len(added_links)} entries to public/{site['filename']}")
    else:
        print(f"  [Skip] 記事が1件も取得できなかったため、XMLは更新しませんでした。")
