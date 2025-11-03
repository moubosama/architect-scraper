from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import json
import os
from bs4 import BeautifulSoup
from database import init_db, insert_architect_row, export_to_excel

# 設定定数
START_NUMBER = 1                    # 検索開始番号
END_NUMBER = 999999                 # 検索終了番号
MAX_CONSECUTIVE_SKIPS = 10000      # 連続スキップの最大回数

PROGRESS_FILE = "scraping_progress.json"

def save_progress(current_number: int, consecutive_skips: int = 0):
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'last_completed': current_number,
            'consecutive_skips': consecutive_skips
        }, f)
    print(f"    💾 進捗を保存しました: 第{current_number}号まで完了 (連続スキップ: {consecutive_skips}回)")

def load_progress() -> tuple:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('last_completed', 0), data.get('consecutive_skips', 0)
        except:
            return 0, 0
    return 0, 0

def clear_progress():
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        print("✅ 進捗ファイルをクリアしました")

def normalize_text(text: str) -> str:
    """全角数字を半角に変換、建築士登録番号から「第」と「号」を削除"""
    if not text:
        return text
    
    text = text.translate(str.maketrans('０１２３４５６７８９', '0123456789'))
    text = re.sub(r'^第(.+?)号$', r'\1', text)
    
    return text

def normalize_architect_data(data: dict) -> dict:
    normalized = {}
    for key, value in data.items():
        if isinstance(value, str):
            normalized[key] = normalize_text(value)
        else:
            normalized[key] = value
    return normalized

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=chrome_options
    )

def search_and_get_links(driver, url: str, search_number: str) -> list:
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
    try:
        li_elements = soup.find_all('li', class_='py-2')
        
        for li_elem in li_elements:
            h3_elem = li_elem.find('h3', class_='text-sm')
            if h3_elem:
                h3_text = h3_elem.get_text(strip=True)
                
                if section_title == h3_text:
                    p_tags = li_elem.find_all('p')
                    
                    for p_tag in p_tags:
                        text = p_tag.get_text(strip=True)
                        if text and text != '　':
                            return text
                    
                    return ''
    except Exception as e:
        print(f"      ⚠️ extract エラー ({section_title}): {str(e)}")
        import traceback
        traceback.print_exc()
    return ''

def extract_name_from_cell(cell):
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
    print(f"  📖 {url} を開いています...")
    
    driver.execute_script(f"window.open('{url}', '_blank');")
    driver.switch_to.window(driver.window_handles[-1])
    time.sleep(5)
    
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
    
    office_info = {
        '事務所登録番号': extract_text_from_section(tab1, '事務所登録番号'),
        '事務所資格区分': extract_text_from_section(tab1, '事務所資格区分'),
        '事務所名称': extract_text_from_section(tab1, '事務所名称'),
        '事務所所在地郵便番号': extract_text_from_section(tab1, '事務所所在地郵便番号'),
        '事務所所在地': extract_text_from_section(tab1, '事務所所在地'),
        '事務所所在地ビル名等': extract_text_from_section(tab1, '事務所所在地ビル名等'),
        '事務所電話番号': extract_text_from_section(tab1, '事務所電話番号'),
    }
    
    try:
        driver.execute_script("document.querySelector('a[href=\"#tab2\"]').click();")
        time.sleep(2)
    except:
        pass
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    tab2 = soup.find('div', id='tab2') or soup
    office_info['法人名称'] = extract_text_from_section(tab2, '法人名称')
    
    office_info = normalize_architect_data(office_info)
    
    print(f"    🏢 {office_info['事務所名称']}")
    
    try:
        driver.execute_script("document.querySelector('a[href=\"#tab4\"]').click();")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, 500);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
    except:
        pass
    
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
        
        managing_architect = normalize_architect_data(managing_architect)
        
        if managing_architect.get('建築士氏名'):
            print(f"    ✓ 管理: {managing_architect['建築士氏名']} ({managing_architect.get('建築士登録番号', '')})")
    
    try:
        driver.execute_script("document.querySelector('a[href=\"#tab5\"]').click();")
        time.sleep(3)
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
    except:
        pass
    
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
                        
                        architect = normalize_architect_data(architect)
                        
                        if name_kanji:
                            affiliate_architects.append(architect)
                            print(f"    ✓ 所属: {name_kanji} ({architect.get('建築士登録番号', '')})")
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
    print("=" * 60)
    print("🚀 建築士事務所スクレイピング開始")
    print("=" * 60)
    print(f"\n【設定】")
    print(f"  開始番号: {START_NUMBER}")
    print(f"  終了番号: {END_NUMBER}")
    print(f"  最大連続スキップ回数: {MAX_CONSECUTIVE_SKIPS}")
    
    last_completed, consecutive_skips = load_progress()
    
    start_num = START_NUMBER
    current_skips = 0
    
    if last_completed > 0:
        print(f"\n⚠️  前回は第{last_completed}号まで完了しています（連続スキップ: {consecutive_skips}回）")
        response = input(f"続きから開始しますか？ (y/n): ").strip().lower()
        if response == 'y':
            start_num = last_completed + 1
            current_skips = consecutive_skips
            print(f"✅ 第{start_num}号から再開します")
        else:
            clear_progress()
            print(f"✅ 最初から開始します")
    
    init_db()
    driver = create_driver()
    
    try:
        target_url = "https://icba.kenchikugyousei-db.jp/knjt01/jimusho?sortCol=rec_no"
        
        print(f"\n【検索範囲】第{start_num}号 ～ 第{END_NUMBER}号")
        
        new_count = 0
        duplicate_count = 0
        total_processed = 0
        
        for search_num in range(start_num, END_NUMBER + 1):
            if current_skips >= MAX_CONSECUTIVE_SKIPS:
                print(f"\n⚠️ 連続で{MAX_CONSECUTIVE_SKIPS}回データが見つかりませんでした")
                print(f"💡 検索を終了します（最終検索番号: 第{search_num - 1}号）")
                break
            
            print(f"\n" + "=" * 60)
            print(f"【検索番号: 第{search_num}号】（連続スキップ: {current_skips}/{MAX_CONSECUTIVE_SKIPS}）")
            print("=" * 60)
            
            try:
                detail_links = search_and_get_links(driver, target_url, str(search_num))
                
                if not detail_links:
                    print(f"❌ 第{search_num}号: リンクが見つかりませんでした")
                    current_skips += 1
                    save_progress(search_num, current_skips)
                    continue
                
                if current_skips > 0:
                    print(f"✅ データが見つかりました！連続スキップカウントをリセットします（{current_skips} → 0）")
                    current_skips = 0
                
                print(f"\n【詳細ページ処理】({len(detail_links)}件)")
                
                for i, link in enumerate(detail_links, 1):
                    print(f"\n[{i}/{len(detail_links)}]")
                    
                    try:
                        data = scrape_detail_page(driver, link)
                        
                        office_info = data['office_info']
                        managing_architect = data['managing_architect']
                        affiliate_architects = data['affiliate_architects']
                        
                        if managing_architect and managing_architect.get('建築士氏名'):
                            result = insert_architect_row(office_info, managing_architect, "管理建築士情報")
                            
                            if "新規登録" in result:
                                new_count += 1
                            elif "重複" in result:
                                duplicate_count += 1
                            
                            total_processed += 1
                            print(f"    💾 {result}")
                        
                        for affiliate in affiliate_architects:
                            result = insert_architect_row(office_info, affiliate, "所属建築士情報")
                            
                            if "新規登録" in result:
                                new_count += 1
                            elif "重複" in result:
                                duplicate_count += 1
                            
                            total_processed += 1
                            print(f"    💾 {result}")
                        
                        time.sleep(2)
                        
                    except Exception as e:
                        print(f"    ❌ エラー: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                save_progress(search_num, current_skips)
                
            except Exception as e:
                print(f"❌ 第{search_num}号の処理中にエラー: {str(e)}")
                import traceback
                traceback.print_exc()
                current_skips += 1
                save_progress(search_num, current_skips)
                continue
        
        print("\n" + "=" * 60)
        print("📊 処理結果サマリー")
        print("=" * 60)
        print(f"  検索範囲: 第{start_num}号 ～ 第{search_num}号")
        print(f"  処理件数: {total_processed}人")
        print(f"  新規登録: {new_count}人")
        print(f"  重複登録: {duplicate_count}人")
        print(f"  最終連続スキップ: {current_skips}回")
        
        print("\n【Excelファイル情報】")
        export_to_excel("architects_export.xlsx")
        
        if current_skips >= MAX_CONSECUTIVE_SKIPS or search_num >= END_NUMBER:
            clear_progress()
        
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