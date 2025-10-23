from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def fetch_html(url: str, search_number: str) -> str:
    chrome_options = Options()
    # ヘッドレスモードをコメントアウト（ブラウザが表示される）
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/118.0.5993.118 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        # ページを開く
        driver.get(url)
        print("📄 ページを読み込み中...")
        
        # ページが完全に読み込まれるまで待機
        time.sleep(3)
        
        # 入力フィールドを見つけて「1」を入力
        print(f"🔢 検索番号「{search_number}」を入力中...")
        input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[wire\\:model\\.defer='filters.toroku_no_jimusho']"))
        )
        input_field.clear()
        input_field.send_keys(search_number)
        
        time.sleep(1)  # 入力後少し待つ
        
        # 検索ボタンをクリック
        print("🔍 検索ボタンをクリック中...")
        search_button = driver.find_element(By.CSS_SELECTOR, "button[type='submit'].bg-green-600")
        search_button.click()
        
        # 検索結果が表示されるまで待機
        print("⏳ 検索結果を待機中...")
        time.sleep(5)  # 結果が読み込まれるまで待つ
        
        # テーブルが表示されるまで待機
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "table"))
            )
            print("✅ 検索結果のテーブルを検出しました")
        except:
            print("⚠️ テーブルが見つかりませんでした（結果がない可能性があります）")
        
        # 最終的なHTMLを取得
        html = driver.page_source
        
        # ブラウザを5秒間表示したままにする（確認用）
        print("👀 結果を5秒間表示します...")
        time.sleep(5)
        
        return html
        
    finally:
        driver.quit()
        print("🚪 ブラウザを閉じました")

if __name__ == "__main__":
    target_url = "https://icba.kenchikugyousei-db.jp/knjt01/jimusho?sortCol=rec_no"
    search_number = "1"  # 検索する番号
    
    html = fetch_html(target_url, search_number)

    with open("output.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"✅ 検索番号「{search_number}」の結果をoutput.htmlに保存しました。")