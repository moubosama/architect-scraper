from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup
from database import init_db, insert_or_update_architect, export_to_csv

def create_driver():
    """Chromeドライバーを作成"""
    chrome_options = Options()
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=chrome_options
    )

def search_and_get_links(driver, url: str, search_number: str) -> list:
    """検索して詳細ページのリンクを全て取得"""
    driver.get(url)
    print("📄 ページを読み込み中...")
    time.sleep(3)

    print(f"🔢 検索番号「{search_number}」を入力中...")
    input_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "input[wire\\:model\\.defer='filters.toroku_no_jimusho']"))
    )
    input_field.clear()
    input_field.send_keys(search_number)
    time.sleep(1)

    print("🔍 検索ボタンをクリック中...")
    search_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'].bg-green-600")
    search_button.click()

    print("⏳ 検索結果を待機中...")
    time.sleep(5)

    # 件数を確認
    try:
        result_count_elem = driver.find_element(By.XPATH, "//*[contains(text(), '件数')]")
        print(f"📊 {result_count_elem.text}")
    except:
        pass

    # 登録番号列のリンクを全て取得
    links = []
    link_elements = driver.find_elements(By.CSS_SELECTOR, "td.link3 a[target='_blank']")
    
    for elem in link_elements:
        href = elem.get_attribute('href')
        if href:
            links.append(href)
    
    print(f"🔗 {len(links)}件のリンクを取得しました")
    return links

def extract_text_from_section(soup, section_title: str) -> str:
    """セクションタイトルから対応するテキストを抽出"""
    try:
        # h3タグでセクションタイトルを探す
        h3_elem = soup.find('h3', class_='text-sm font-semibold text-gray-800', string=lambda text: text and section_title in text)
        if h3_elem:
            # 次のpタグからテキストを取得
            p_elem = h3_elem.find_next('p', class_='mt-1 text-sm text-gray-600')
            if p_elem:
                text = p_elem.get_text(strip=True)
                # ＊＊＊ の場合は空文字に
                if text == '＊＊＊' or text == '　':
                    return ''
                return text
    except:
        pass
    return ''

def scrape_detail_page(driver, url: str) -> list:
    """
    詳細ページをスクレイピングして建築士情報を取得
    戻り値: 建築士情報のリスト（管理建築士 + 所属建築士）
    """
    print(f"  📖 {url} を開いています...")
    
    # 新しいタブで開く
    driver.execute_script(f"window.open('{url}', '_blank');")
    
    # 新しいタブに切り替え
    driver.switch_to.window(driver.window_handles[-1])
    
    time.sleep(3)
    
    # ページをスクロールして遅延読み込みコンテンツを表示
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # タブを切り替えて所属建築士情報を表示
    try:
        # 所属建築士タブ(#tab5)をクリック
        driver.execute_script("document.querySelector('a[href=\"#tab5\"]').click();")
        time.sleep(3)
    except:
        pass
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    architects = []
    
    # ============================================
    # 事務所情報（共通）
    # ============================================
    office_info = {
        'office_registration_number': extract_text_from_section(soup, '事務所登録番号'),
        'company_name': extract_text_from_section(soup, '法人名称'),
        'office_qualification': extract_text_from_section(soup, '事務所資格区分'),
        'office_name': extract_text_from_section(soup, '事務所名称'),
        'office_postal_code': extract_text_from_section(soup, '事務所所在地郵便番号'),
        'office_address': extract_text_from_section(soup, '事務所所在地'),
        'office_building': extract_text_from_section(soup, '事務所所在地ビル名等'),
        'office_phone': extract_text_from_section(soup, '事務所電話番号'),
    }
    
    print(f"    📋 事務所: {office_info['office_name']}")
    
    # ============================================
    # 管理建築士情報 (#tab4)
    # ============================================
    # tab4の内容を探す
    tab4 = soup.find('div', id='tab4')
    if tab4:
        managing_architect = office_info.copy()
        managing_architect.update({
            'architect_name_kana': extract_text_from_section(tab4, '建築士氏名フリガナ'),
            'architect_name': extract_text_from_section(tab4, '建築士氏名'),
            'architect_category': extract_text_from_section(tab4, '建築士区分'),
            'architect_registration_number': extract_text_from_section(tab4, '建築士登録番号'),
            'registration_prefecture': extract_text_from_section(tab4, '登録を受けた都道府県名'),
            'is_managing_architect': True
        })
        
        if managing_architect.get('architect_name'):
            architects.append(managing_architect)
            print(f"    ✓ 管理建築士: {managing_architect['architect_name']} ({managing_architect['architect_category']})")
    
    # ============================================
    # 所属建築士情報 (#tab5)
    # ============================================
    # もう一度スクロールして確実に読み込む
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(2)
    
    # 最新のHTMLを取得
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # tab5の内容を探す
    tab5 = soup.find('div', id='tab5')
    if tab5:
        # テーブルから所属建築士を抽出
        # Livewireで動的に読み込まれるため、テーブル構造を探す
        tables = tab5.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # ヘッダー行をスキップ
                cells = row.find_all('td')
                if len(cells) >= 5:  # 十分な列数がある場合
                    try:
                        architect = office_info.copy()
                        
                        # テーブルの列からデータを抽出
                        # 通常: フリガナ, 氏名, 区分, 登録番号, 都道府県
                        architect.update({
                            'architect_name_kana': cells[0].get_text(strip=True),
                            'architect_name': cells[1].get_text(strip=True),
                            'architect_category': cells[2].get_text(strip=True),
                            'architect_registration_number': cells[3].get_text(strip=True),
                            'registration_prefecture': cells[4].get_text(strip=True) if len(cells) > 4 else '',
                            'is_managing_architect': False
                        })
                        
                        # ＊＊＊を空文字に変換
                        for key in architect:
                            if isinstance(architect[key], str) and architect[key] == '＊＊＊':
                                architect[key] = ''
                        
                        if architect.get('architect_name') and architect['architect_name'] != '':
                            architects.append(architect)
                            print(f"    ✓ 所属建築士: {architect['architect_name']} ({architect['architect_category']})")
                    except Exception as e:
                        print(f"    ⚠️ 所属建築士の抽出エラー: {str(e)}")
                        continue
    
    # タブを閉じる
    driver.close()
    
    # 元のタブに戻る
    driver.switch_to.window(driver.window_handles[0])
    
    print(f"  ✅ {len(architects)}人の建築士情報を取得")
    
    return architects

def main():
    """メイン処理"""
    print("=" * 60)
    print("🚀 建築士事務所スクレイピング開始")
    print("=" * 60)
    
    # DB初期化
    init_db()
    
    driver = create_driver()
    
    try:
        target_url = "https://icba.kenchikugyousei-db.jp/knjt01/jimusho?sortCol=rec_no"
        search_number = "1"
        
        # 1. 検索して詳細ページのリンクを全て取得
        print("\n【ステップ1】検索実行")
        detail_links = search_and_get_links(driver, target_url, search_number)
        
        if not detail_links:
            print("❌ リンクが見つかりませんでした")
            return
        
        # 2. 各詳細ページを順番に処理
        print(f"\n【ステップ2】詳細ページ処理（{len(detail_links)}件）")
        
        new_count = 0
        update_count = 0
        skip_count = 0
        error_count = 0
        
        for i, link in enumerate(detail_links, 1):
            print(f"\n[{i}/{len(detail_links)}] 処理中...")
            
            try:
                architects = scrape_detail_page(driver, link)
                
                for architect in architects:
                    result = insert_or_update_architect(architect)
                    
                    if "新規登録" in result:
                        new_count += 1
                    elif "更新" in result:
                        update_count += 1
                    elif "スキップ" in result:
                        skip_count += 1
                    
                    print(f"    💾 {result}")
                
                time.sleep(2)  # サーバー負荷軽減
                
            except Exception as e:
                error_count += 1
                print(f"    ❌ エラー: {str(e)}")
                import traceback
                traceback.print_exc()
                # エラーが起きても続行
                continue
        
        # 3. 結果サマリー
        print("\n" + "=" * 60)
        print("📊 処理結果サマリー")
        print("=" * 60)
        print(f"新規登録: {new_count}人")
        print(f"更新: {update_count}人")
        print(f"スキップ（重複）: {skip_count}人")
        print(f"エラー: {error_count}件")
        print(f"合計処理: {new_count + update_count + skip_count}人")
        
        # 4. CSVエクスポート
        print("\n【ステップ3】CSVエクスポート")
        export_to_csv("architects_export.csv")
        
        print("\n✅ 全ての処理が完了しました！")
        
    except Exception as e:
        print(f"\n❌ メイン処理でエラーが発生: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        driver.quit()
        print("\n🚪 ブラウザを閉じました")

if __name__ == "__main__":
    main()