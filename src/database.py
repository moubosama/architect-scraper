import mysql.connector
from mysql.connector import Error
import openpyxl
from openpyxl.styles import Font
from datetime import datetime
import os

# MySQL接続設定
DB_CONFIG = {
    'host': '127.0.0.1',
    'port': 3306,
    'user': 'root',
    'password': 'root',  # 環境に合わせて変更してください
    'database': 'scraping_db'
}

EXCEL_FILE = "architects_export.xlsx"

def create_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"❌ MySQL接続エラー: {e}")
        return None

def init_db():
    conn = create_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS 建築士情報 (
        id INT AUTO_INCREMENT PRIMARY KEY,
        重複 VARCHAR(50) DEFAULT '',
        事務所登録番号 VARCHAR(255),
        法人名称 VARCHAR(255),
        事務所資格区分 VARCHAR(100),
        事務所名称 VARCHAR(255),
        事務所所在地郵便番号 VARCHAR(20),
        事務所所在地 TEXT,
        事務所所在地ビル名等 TEXT,
        事務所電話番号 VARCHAR(50),
        建築士情報 VARCHAR(50) DEFAULT '',
        建築士氏名フリガナ VARCHAR(255),
        建築士氏名 VARCHAR(255),
        建築士区分 VARCHAR(100),
        建築士登録番号 VARCHAR(255),
        登録を受けた都道府県名 VARCHAR(100),
        created_at DATETIME,
        updated_at DATETIME,
        INDEX idx_architect (建築士登録番号, 建築士区分, 建築士氏名)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ データベースを初期化しました")
    
    init_excel()

def init_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "建築士情報"
        
        columns = [
            '重複',
            '事務所登録番号', '法人名称', '事務所資格区分', '事務所名称',
            '事務所所在地郵便番号', '事務所所在地', '事務所所在地ビル名等', '事務所電話番号',
            '建築士情報',
            '建築士氏名フリガナ', '建築士氏名', '建築士区分',
            '建築士登録番号', '登録を受けた都道府県名'
        ]
        ws.append(columns)
        
        for cell in ws[1]:
            cell.font = Font(bold=True)
        
        wb.save(EXCEL_FILE)
        print(f"✅ Excelファイルを初期化しました: {EXCEL_FILE}")

def append_to_excel(row_data: tuple):
    try:
        if os.path.exists(EXCEL_FILE):
            wb = openpyxl.load_workbook(EXCEL_FILE)
            ws = wb.active
        else:
            init_excel()
            wb = openpyxl.load_workbook(EXCEL_FILE)
            ws = wb.active
        
        ws.append(row_data)
        wb.save(EXCEL_FILE)
    except Exception as e:
        print(f"⚠️ Excel書き込みエラー: {e}")

def insert_architect_row(office_info: dict, architect: dict, architect_type: str) -> str:
    """
    建築士情報をDBに挿入し、Excelにも追記
    重複チェック: 建築士登録番号、建築士区分、建築士氏名の3つが一致で重複判定
    """
    conn = create_connection()
    if not conn:
        return "接続エラー"
    
    cursor = conn.cursor()
    now = datetime.now()
    
    try:
        # 重複チェック（建築士登録番号、区分、氏名）
        cursor.execute("""
            SELECT id FROM 建築士情報
            WHERE 建築士登録番号 = %s 
            AND 建築士区分 = %s
            AND 建築士氏名 = %s
        """, (
            architect.get('建築士登録番号', ''),
            architect.get('建築士区分', ''),
            architect.get('建築士氏名', '')
        ))
        
        existing = cursor.fetchone()
        
        excel_row = (
            '重複' if existing else '',
            office_info.get('事務所登録番号', ''),
            office_info.get('法人名称', ''),
            office_info.get('事務所資格区分', ''),
            office_info.get('事務所名称', ''),
            office_info.get('事務所所在地郵便番号', ''),
            office_info.get('事務所所在地', ''),
            office_info.get('事務所所在地ビル名等', ''),
            office_info.get('事務所電話番号', ''),
            architect_type,
            architect.get('建築士氏名フリガナ', ''),
            architect.get('建築士氏名', ''),
            architect.get('建築士区分', ''),
            architect.get('建築士登録番号', ''),
            architect.get('登録を受けた都道府県名', '')
        )
        
        if existing:
            # 重複: Excelにのみ追加
            append_to_excel(excel_row)
            result = f"重複検出: {architect.get('建築士氏名')} (Excelにのみ記録)"
        else:
            # 新規: DBとExcel両方に追加
            cursor.execute("""
                INSERT INTO 建築士情報 (
                    重複,
                    事務所登録番号, 法人名称, 事務所資格区分,
                    事務所名称, 事務所所在地郵便番号, 事務所所在地,
                    事務所所在地ビル名等, 事務所電話番号,
                    建築士情報,
                    建築士氏名フリガナ, 建築士氏名, 建築士区分,
                    建築士登録番号, 登録を受けた都道府県名,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                '',
                office_info.get('事務所登録番号', ''),
                office_info.get('法人名称', ''),
                office_info.get('事務所資格区分', ''),
                office_info.get('事務所名称', ''),
                office_info.get('事務所所在地郵便番号', ''),
                office_info.get('事務所所在地', ''),
                office_info.get('事務所所在地ビル名等', ''),
                office_info.get('事務所電話番号', ''),
                architect_type,
                architect.get('建築士氏名フリガナ', ''),
                architect.get('建築士氏名', ''),
                architect.get('建築士区分', ''),
                architect.get('建築士登録番号', ''),
                architect.get('登録を受けた都道府県名', ''),
                now, now
            ))
            conn.commit()
            append_to_excel(excel_row)
            result = f"新規登録: {architect.get('建築士氏名')} ({architect_type})"
    
    except Error as e:
        result = f"エラー: {str(e)}"
    finally:
        cursor.close()
        conn.close()
    
    return result

def export_to_excel(filename: str = "architects_export.xlsx"):
    """最終統計情報を表示"""
    if os.path.exists(filename):
        wb = openpyxl.load_workbook(filename)
        ws = wb.active
        row_count = ws.max_row - 1
        
        print(f"✅ Excelファイル: {filename}")
        print(f"   - 総行数: {row_count}件")
    else:
        print(f"⚠️ Excelファイルが見つかりません: {filename}")