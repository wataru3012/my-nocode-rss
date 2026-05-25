import os
import urllib.request
import re
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator

def main():
    # 1. 2枚目の画像の「すべての記事一覧」ページURLを設定
    url = "https://androidjiten.com/archives/sitemap"
    
    # 一般的なブラウザ（Chrome）のふりをしてサイトのブロックを回避するヘッダー
    req = urllib.request.Request(
        url, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ja,en-US;q=0.7,en;q=0.3'
        }
    )
    
    try:
        html = urllib.request.urlopen(req, timeout=15).read()
    except Exception as e:
        print(f"【エラー】サイトのHTML取得に失敗しました: {e}")
        return

    soup = BeautifulSoup(html, 'html.parser')
    
    # 2. RSSフィードの初期化
    fg = FeedGenerator()
    fg.id(url)
    fg.title('アンドロイド事典 カスタムRSS')
    fg.author({'name': 'GitHub Actions RSS Bot'})
    fg.link(href=url, rel='alternate')
    fg.description('androidjiten.com の全記事一覧から自動生成したRSSフィードです。')
    fg.language('ja')

    # 3. 2枚目の画像の構造（li.post-item）を正確に抽出
    items = soup.select('.post-item')
    if not items:
        print("【エラー】HTML内に '.post-item' 要素が見つかりませんでした。サイトの構造が変わったか、アクセスがブロックされている可能性があります。")
        return

    print(f"検出された記事数: {len(items)} 件")

    # 最新の15件〜20件程度をRSSに入れる（全件入れるとXMLが巨大化するため）
    for item in items[:30]:
        a_tag = item.select_one('a')
        if not a_tag:
            continue
            
        title = a_tag.get_text(strip=True)
        link = a_tag.get('href')
        
        if not title or not link:
            continue

        # フィードに記事を追加
        fe = fg.add_entry()
        fe.id(link)
        fe.title(title)
        fe.link(href=link)
        fe.description(title) # 箇条書きのため、概要にはタイトルをそのままセットします

    # 4. publicディレクトリを作ってXMLを書き出し
    os.makedirs('public', exist_ok=True)
    fg.rss_file('public/androidjiten.xml', pretty=True)
    print("【成功】public/androidjiten.xml を正常に生成しました。")

if __name__ == '__main__':
    main()
