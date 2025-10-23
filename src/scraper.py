from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def fetch_html(url: str) -> str:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                "AppleWebKit/537.36 (KHTML, like Gecko) "
                                "Chrome/118.0.5993.118 Safari/537.36")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(url)

    html = driver.page_source
    driver.quit()
    return html

if __name__ == "__main__":
    target_url = "https://icba.kenchikugyousei-db.jp/knjt01/jimusho?sortCol=rec_no"
    html = fetch_html(target_url)

    with open("output.html", "w", encoding="utf-8") as f:
        f.write(html)

    print("✅ HTMLを output.html に保存しました。")
