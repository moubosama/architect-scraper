from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
from bs4 import BeautifulSoup
from database import init_db, insert_architect_row, export_to_excel

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

    try:
        result_count_elem = driver.find_element(By.XPATH, "//*[contains(text(), '件数')]")
        print(f"📊 {result_count_elem.text}")
    except:
        pass

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
        li_elements = soup.find_all('li', class_='py-2')
        
        for li_elem in li_elements:
            # h3タグを探す
            h3_elem = li_elem.find('h3', class_='text-sm')
            if h3_elem:
                h3_text = h3_elem.get_text(strip=True)
                
                # 完全一致のみ（部分一致を除外）
                if section_title == h3_text:
                    # 同じli内のすべてのpタグを取得
                    p_tags = li_elem.find_all('p')
                    
                    # pタグの中身を確認
                    for p_tag in p_tags:
                        text = p_tag.get_text(strip=True)
                        # 空白文字のみスキップ
                        if text and text != '　':
                            return text
                    
                    # pタグがない場合
                    return ''
    except Exception as e:
        print(f"      ⚠️ extract エラー ({section_title}): {str(e)}")
        import traceback
        traceback.print_exc()
    return ''

def extract_name_from_cell(cell):
    """氏名セルからカナと漢字を抽出"""
    html = str(cell)
    parts = re.split(r'<br\s*/?>', html, flags=re.IGNORECASE)
    
    clean_parts = []
    for part in parts:
        text = re.sub(r'<[^>]+>', '', part).strip()
        if text:
            clean_parts.append(text)
    
    if len(clean_parts) >= 2:
        return clean_parts[0], clean_parts[1]
    elif len(clean_parts) == 1:
        return clean_parts[0], clean_parts[0]
    else:
        return '', ''

def scrape_detail_page(driver, url: str) -> dict:
    """詳細ページをスクレイピングして情報を取得"""
    print(f"  📖 {url} を開いています...")
    
    driver.execute_script(f"window.open('{url}', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(5)
    
    # まず確実にtab1をクリックしてページ全体を読み込む
    try:
        driver.execute_script("document.querySelector('a[href=\"#tab1\"]').click();")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
    except:
        pass
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    tab1 = soup.find('div', id='tab1') or soup
    
    # デバッグ用：HTMLの一部を出力
    print("    🔍 HTMLデバッグ:")
    li_elements = tab1.find_all('li', class_='py-2')
    for li in li_elements:
        h3 = li.find('h3')
        p = li.find('p')
        if h3 and '事務所所在地' in h3.get_text():
            h3_text = h3.get_text(strip=True)
            p_text = p.get_text(strip=True) if p else 'なし'
            print(f"       {h3_text}: {p_text}")
    
    office_info = {
        '事務所登録番号': extract_text_from_section(tab1, '事務所登録番号'),
        '事務所資格区分': extract_text_from_section(tab1, '事務所資格区分'),
        '事務所名称': extract_text_from_section(tab1, '事務所名称'),
        '事務所所在地郵便番号': extract_text_from_section(tab1, '事務所所在地郵便番号'),
        '事務所所在地': extract_text_from_section(tab1, '事務所所在地'),
        '事務所所在地ビル名等': extract_text_from_section(tab1, '事務所所在地ビル名等'),
        '事務所電話番号': extract_text_from_section(tab1, '事務所電話番号'),
    }
    
    # デバッグ出力
    print(f"    📝 取得データ:")
    print(f"       登録番号: {office_info['事務所登録番号']}")
    print(f"       郵便番号: {office_info['事務所所在地郵便番号']}")
    print(f"       所在地: {office_info['事務所所在地']}")
    print(f"       ビル名: {office_info['事務所所在地ビル名等']}")
    print(f"       電話: {office_info['事務所電話番号']}")
    
    # tab2（申請者情報）
    try:
        driver.execute_script("document.querySelector('a[href=\"#tab2\"]').click();")
        time.sleep(2)
    except:
        pass
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    tab2 = soup.find('div', id='tab2') or soup
    office_info['法人名称'] = extract_text_from_section(tab2, '法人名称')
    
    print(f"    🏢 {office_info['事務所名称']}")
    
    # tab4（管理建築士情報）
    try:
        driver.execute_script("document.querySelector('a[href=\"#tab4\"]').click();")
        time.sleep(3)  # 待機時間を延長
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
    except:
        pass
    
    # tab4のHTMLを再取得
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    tab4 = soup.find('div', id='tab4')
    
    managing_architect = None
    if tab4:
        managing_architect = office_info.copy()
        managing_architect.update({
            '建築士氏名フリガナ': extract_text_from_section(tab4, '建築士氏名フリガナ'),
            '建築士氏名': extract_text_from_section(tab4, '建築士氏名'),
            '建築士区分': extract_text_from_section(tab4, '建築士区分'),
            '建築士登録番号': extract_text_from_section(tab4, '建築士登録番号'),
            '登録を受けた都道府県名': extract_text_from_section(tab4, '登録を受けた都道府県名'),
        })
        
        if managing_architect.get('建築士氏名'):
            print(f"    ✓ 管理: {managing_architect['建築士氏名']} ({managing_architect.get('建築士登録番号', '')})")
    
    # tab5（所属建築士情報）
    try:
        driver.execute_script("document.querySelector('a[href=\"#tab5\"]').click();")
        time.sleep(3)  # 待機時間を延長
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
    except:
        pass
    
    # tab5のHTMLを再取得
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    tab5 = soup.find('div', id='tab5')
    
    affiliate_architects = []
    if tab5:
        tables = tab5.find_all('table')
        
        for table in tables:
            tbody = table.find('tbody')
            if not tbody:
                continue
                
            rows = tbody.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    try:
                        architect = office_info.copy()
                        
                        first_cell_text = cells[0].get_text(strip=True)
                        
                        if first_cell_text.isdigit():
                            name_cell = cells[1]
                            category_cell = cells[2]
                            reg_num_cell = cells[3] if len(cells) > 3 else None
                        else:
                            name_cell = cells[0]
                            category_cell = cells[1]
                            reg_num_cell = cells[2] if len(cells) > 2 else None
                        
                        name_kana, name_kanji = extract_name_from_cell(name_cell)
                        
                        category_html = str(category_cell)
                        category_parts = re.split(r'<br\s*/?>', category_html, flags=re.IGNORECASE)
                        category_clean = []
                        for part in category_parts:
                            text = re.sub(r'<[^>]+>', '', part).strip()
                            if text:
                                category_clean.append(text)
                        
                        category = category_clean[0] if category_clean else ''
                        registration_pref = category_clean[1] if len(category_clean) > 1 else ''
                        
                        reg_number = reg_num_cell.get_text(strip=True) if reg_num_cell else ''
                        if reg_number in ['＊＊＊', '　']:
                            reg_number = ''
                        
                        architect.update({
                            '建築士氏名フリガナ': name_kana,
                            '建築士氏名': name_kanji,
                            '建築士区分': category,
                            '建築士登録番号': reg_number,
                            '登録を受けた都道府県名': registration_pref,
                        })
                        
                        if name_kanji:
                            affiliate_architects.append(architect)
                            print(f"    ✓ 所属: {name_kanji}")
                    except Exception as e:
                        print(f"    ⚠️ エラー: {str(e)}")
                        continue
    
    driver.close()
    driver.switch_to.window(driver.window_handles[0])
    
    return {
        'office_info': office_info,
        'managing_architect': managing_architect,
        'affiliate_architects': affiliate_architects
    }

def main():
    """メイン処理"""
    print("=" * 60)
    print("🚀 建築士事務所スクレイピング開始")
    print("=" * 60)
    
    init_db()
    driver = create_driver()
    
    try:
        target_url = "https://icba.kenchikugyousei-db.jp/knjt01/jimusho?sortCol=rec_no"
        search_number = "1"
        
        print("\n【ステップ1】検索実行")
        detail_links = search_and_get_links(driver, target_url, search_number)
        
        if not detail_links:
            print("❌ リンクが見つかりませんでした")
            return
        
        print(f"\n【ステップ2】詳細ページ処理（{len(detail_links)}件）")
        
        new_count = 0
        update_count = 0
        skip_count = 0
        
        for i, link in enumerate(detail_links, 1):
            print(f"\n[{i}/{len(detail_links)}]")
            
            try:
                data = scrape_detail_page(driver, link)
                
                office_info = data['office_info']
                managing_architect = data['managing_architect']
                affiliate_architects = data['affiliate_architects']
                
                # 管理建築士を1行として登録
                if managing_architect and managing_architect.get('建築士氏名'):
                    result = insert_architect_row(office_info, managing_architect, "管理建築士情報")
                    
                    if "新規登録" in result:
                        new_count += 1
                    elif "更新" in result:
                        update_count += 1
                    elif "スキップ" in result:
                        skip_count += 1
                    
                    print(f"    💾 {result}")
                
                # 所属建築士を1人ずつ1行として登録
                for affiliate in affiliate_architects:
                    result = insert_architect_row(office_info, affiliate, "所属建築士情報")
                    
                    if "新規登録" in result:
                        new_count += 1
                    elif "更新" in result:
                        update_count += 1
                    elif "スキップ" in result:
                        skip_count += 1
                    
                    print(f"    💾 {result}")
                
                time.sleep(2)
                
            except Exception as e:
                print(f"    ❌ エラー: {str(e)}")
                import traceback
                traceback.print_exc()
                continue
        
        print("\n" + "=" * 60)
        print("📊 処理結果サマリー")
        print("=" * 60)
        print(f"  新規: {new_count}人 / 更新: {update_count}人")
        print(f"  スキップ: {skip_count}件")
        
        print("\n【ステップ3】Excelエクスポート")
        export_to_excel("architects_export.xlsx")
        
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