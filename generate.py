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

    # 💡 共通判定：URLの末尾が /feed または /feed/ ならXMLフィードモードとみなす
    is_xml_feed = site['url'].endswith('/feed') or site['url'].endswith('/feed/')

    for page_num in range(1, max_pages + 1):
        target_url = site['url']
        
        if page_num > 1:
            # 💡 404対策：サイトの形式に合わせてページネーションURLを自動分岐
            if is_xml_feed:
                # WordPressのRSSフィード過去ログ形式 (?paged=2)
                join_char = '&' if '?' in site['url'] else '?'
                target_url = f"{site['url']}{join_char}paged={page_num}"
            elif "hatenablog" in site['url'] or "impress" in site['url']:
                # はてなブログやインプレス系の過去ログ形式
                join_char = '&' if '?' in site['url'] else '?'
                target_url = f"{site['url']}{join_char}page={page_num}&p={page_num}"
            else:
                # 通常のWordPress等のHTML：末尾のスラッシュを考慮して /page/2/ の形を作る
                base_url = site['url'].rstrip('/')
                target_url = f"{base_url}/page/{page_num}/"
                
            print(f"  -> Fetching Page {page_num}: {target_url}")

        try:
            # ⏳ 429（連続アクセス拒否）対策
            if page_num > 1:
                # はてなブログ(規制が厳しい)は5秒、それ以外は3.5秒待機
                wait_time = 5.0 if "hatenablog" in site['url'] else 3.5
                time.sleep(wait_time)

            response = scraper.get(target_url, timeout=15)
            
            if response.status_code != 200:
                print(f"   [Page End] ステータスコード: {response.status_code}")
                break
            html = response.text
        except Exception as e:
            print(f"   [Page Skip] アクセス失敗: {e}")
            break

        # 💡 RSSフィード(XML)の場合は 'xml' パーサー、通常のHTMLは 'html.parser' を自動切り替え
        parser_type = 'xml' if is_xml_feed else 'html.parser'
        soup = BeautifulSoup(html, parser_type)
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
            
            if t_el and l_el:
                # 💡 二刀流ロジック：フィードなら中のテキスト、HTMLならhref属性からURLを取得
                if is_xml_feed:
                    link_url = l_el.get_text(strip=True)
                else:
                    link_url = l_el.get('href')
                
                if not link_url:
                    continue
                    
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
