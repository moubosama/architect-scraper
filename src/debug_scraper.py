from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import time
from bs4 import BeautifulSoup

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=chrome_options
    )

def debug_tab5():
    driver = create_driver()
    
    try:
        url = "https://icba.kenchikugyousei-db.jp/knjt01/jimusho/234514/10"
        
        print(f"📖 {url} を開いています...")
        driver.get(url)
        time.sleep(5)
        
        # tab5をクリック
        print("\n=== tab5（所属建築士情報）をクリック ===")
        driver.execute_script("document.querySelector('a[href=\"#tab5\"]').click();")
        time.sleep(3)
        
        # スクロール
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)
        
        # HTMLをファイルに保存
        with open('debug_tab5.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        print("✓ debug_tab5.html に保存しました\n")
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        tab5 = soup.find('div', id='tab5')
        
        if tab5:
            print("✓ tab5が見つかりました\n")
            
            # テーブルを探す
            tables = tab5.find_all('table')
            print(f"<table>タグ数: {len(tables)}")
            
            # divやulなどの構造も確認
            divs = tab5.find_all('div', recursive=False)
            print(f"直下の<div>数: {len(divs)}")
            
            uls = tab5.find_all('ul')
            print(f"<ul>タグ数: {len(uls)}")
            
            # すべてのテキストを表示（最初の1000文字）
            print(f"\ntab5のテキスト内容（最初の1000文字）:")
            print("-" * 60)
            text = tab5.get_text()[:1000]
            print(text)
            print("-" * 60)
            
            # "ヤマダ"を含む要素を探す
            print("\n「ヤマダ」を含む要素を探す:")
            all_elements = tab5.find_all(string=lambda text: text and 'ヤマダ' in text)
            for idx, elem in enumerate(all_elements):
                parent = elem.parent
                print(f"  [{idx}] {parent.name} タグ: {elem.strip()[:100]}")
            
            # div.grid構造を確認
            print("\n<div class=\"grid\">を探す:")
            grid_divs = tab5.find_all('div', class_='grid')
            print(f"grid divの数: {len(grid_divs)}")
            
            for idx, grid in enumerate(grid_divs[:2]):  # 最初の2つのみ
                print(f"\n  grid[{idx}]:")
                child_divs = grid.find_all('div', recursive=False)
                print(f"    子div数: {len(child_divs)}")
                for child_idx, child in enumerate(child_divs[:3]):
                    print(f"      子div[{child_idx}]: {child.get_text(strip=True)[:100]}")
        
        input("\n[Enter]キーを押すと終了します...")
        
    finally:
        driver.quit()

if __name__ == "__main__":
    debug_tab5()