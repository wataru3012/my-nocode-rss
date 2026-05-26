import os
import json
import cloudscraper
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

# 1. 設定ファイルの読み込み
with open('config.json', 'r', encoding='utf-8') as f:
    sites = json.load(f)

# ボットフィルターを自動で回避するスクレイパー
scraper = cloudscraper.create_scraper()

for site in sites:
    # config.jsonに "pages" の指定があればその数、なければ1ページのみ
    max_pages = site.get('pages', 1)
    print(f"Generating: {site['title']} (Target: {max_pages} pages)")
    
    # フィードの初期化（ループの外で行うことで、全ページの記事を1つに合体させます）
    fg = FeedGenerator()
    fg.id(site['url'])
    fg.title(site['title'])
    fg.link(href=site['url'], rel='alternate')
    fg.description(site['title'])
    
    # 重複して同じ記事を追加しないようにURLを記憶するセット
    added_links = set()

    # 🔄 指定されたページ数分、URLを切り替えながら連続でHTMLを取得
    for page_num in range(1, max_pages + 1):
        target_url = site['url']
        
        # 2ページ目以降のURLの変形ロジック（一般的な ?page=2 や ?p=2 を自動付与）
        if page_num > 1:
            join_char = '&' if '?' in site['url'] else '?'
            target_url = f"{site['url']}{join_char}page={page_num}&p={page_num}"
            print(f"  -> Fetching Page {page_num}: {target_url}")

        try:
            response = scraper.get(target_url, timeout=15)
            # もしページが存在しなくて404エラーなどが返ってきたら、そこでこのサイトのループを終了
            if response.status_code != 200:
                print(f"   [Page End] ステータスコード: {response.status_code}")
                break
            html = response.text
        except Exception as e:
            print(f"   [Page Skip] アクセス失敗: {e}")
            break # 通信エラーが起きた場合も、それ移行のページはスキップして次へ

        soup = BeautifulSoup(html, 'html.parser')

        # 各要素を抽出
        items = soup.select(site['item_selector'])
        if not items:
            # セレクタで何も取れなかったら、最後のページに到達したとみなしてループを抜ける
            break

        for item in items[:100]:
            t_el = item.select_one(site['title_selector'])
            l_el = item.select_one(site['link_selector'])
            
            if t_el and l_el and l_el.get('href'):
                link_url = l_el.get('href')
                
                # 💡【重要】複数ページにまたがると、同じ固定記事などが重複することがあるため防ぐ
                if link_url in added_links:
                    continue
                
                fe = fg.add_entry()
                fe.id(link_url)
                fe.title(t_el.get_text(strip=True))
                fe.link(href=link_url)
                
                # 追加済みのリンクとして記憶
                added_links.add(link_url)

    # 全ページの抽出が終わったら、RSSファイルとして保存
    if added_links:
        os.makedirs('public', exist_ok=True)
        fg.rss_file(f"public/{site['filename']}", pretty=True)
        print(f"  [Success] Saved {len(added_links)} entries to public/{site['filename']}")
    else:
        print(f"  [Skip] 記事が1件も取得できなかったため、XMLは更新しませんでした。")
