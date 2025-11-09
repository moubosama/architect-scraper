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

def get_excel_filename():
    """現在時刻に基づいたExcelファイル名を生成"""
    now = datetime.now()
    return f"architects_export_{now.strftime('%Y-%m-%d-%H')}.xlsx"

EXCEL_FILE = get_excel_filename()

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
        ステータス INT DEFAULT 0,
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
        登録都道府県 VARCHAR(100),
        created_at DATETIME,
        updated_at DATETIME,
        INDEX idx_architect (建築士登録番号, 建築士区分, 建築士氏名),
        INDEX idx_office (事務所登録番号, 法人名称),
        INDEX idx_status (ステータス)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS summary_history (
        id INT AUTO_INCREMENT PRIMARY KEY,
        事務所登録番号 VARCHAR(255),
        登録県名 VARCHAR(100),
        登録人数 INT DEFAULT 0,
        created_at DATETIME,
        INDEX idx_office_reg (事務所登録番号),
        INDEX idx_created (created_at)
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
            '重複', '所属重複', '事務所登録重複',
            '事務所登録番号', '事務所所在地郵便番号', '事務所所在地',
            '法人名称', '事務所資格区分', '事務所名称', '事務所所在地ビル名等',
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
    
    重複チェック:
    1. 完全重複(ステータス=1): 建築士登録番号 + 区分 + 氏名 + 法人名称 が同じ
    2. 所属重複(ステータス=2): 建築士登録番号 + 区分 + 氏名 が同じで法人が異なる
    3. 事務所重複(ステータス=3): 事務所登録番号 + 法人 + 建築士登録番号 + 氏名 + 区分 が全て同じ
    """
    conn = create_connection()
    if not conn:
        return "接続エラー"
    
    cursor = conn.cursor()
    now = datetime.now()
    
    try:
        architect_reg_no = architect.get('建築士登録番号', '')
        architect_name = architect.get('建築士氏名', '')
        architect_category = architect.get('建築士区分', '')
        corporation_name = office_info.get('法人名称', '')
        office_reg_no = office_info.get('事務所登録番号', '')
        registration_pref = office_info.get('登録都道府県', '')
        
        # 1. 完全重複チェック（事務所登録番号 + 法人名称 + 建築士登録番号 + 氏名 + 区分が全て同じ）
        cursor.execute("""
            SELECT id FROM 建築士情報
            WHERE 事務所登録番号 = %s
            AND 法人名称 = %s
            AND 建築士登録番号 = %s 
            AND 建築士氏名 = %s
            AND 建築士区分 = %s
        """, (office_reg_no, corporation_name, architect_reg_no, architect_name, architect_category))
        
        complete_duplicate = cursor.fetchone()
        
        # 2. 事務所重複チェック（同じ法人の異なる事務所に同じ建築士がいる）
        cursor.execute("""
            SELECT id, 事務所登録番号 FROM 建築士情報
            WHERE 法人名称 = %s
            AND 事務所登録番号 != %s
            AND 建築士登録番号 = %s
            AND 建築士氏名 = %s
            AND 建築士区分 = %s
        """, (corporation_name, office_reg_no, architect_reg_no, architect_name, architect_category))
        
        office_duplicates = cursor.fetchall()
        
        # 3. 所属重複チェック（異なる法人に同じ建築士がいる）
        cursor.execute("""
            SELECT id, 法人名称, 事務所登録番号 FROM 建築士情報
            WHERE 法人名称 != %s
            AND 建築士登録番号 = %s 
            AND 建築士氏名 = %s
            AND 建築士区分 = %s
        """, (corporation_name, architect_reg_no, architect_name, architect_category))
        
        affiliation_duplicates = cursor.fetchall()
        
        office_duplicate = cursor.fetchone()
        
        # ステータス判定
        duplicate_flag = ''
        affiliation_flag = ''
        office_flag = ''
        
        if complete_duplicate:
            # 完全重複: Excelにのみ追加、DBには入れない
            duplicate_flag = '重複'
            excel_row = (
                duplicate_flag,
                affiliation_flag,
                office_flag,
                office_info.get('事務所登録番号', ''),
                office_info.get('事務所所在地郵便番号', ''),
                office_info.get('事務所所在地', ''),
                office_info.get('法人名称', ''),
                office_info.get('事務所資格区分', ''),
                office_info.get('事務所名称', ''),
                office_info.get('事務所所在地ビル名等', ''),
                architect.get('建築士氏名フリガナ', ''),
                architect.get('建築士氏名', ''),
                architect.get('建築士区分', ''),
                architect.get('建築士登録番号', ''),
                architect.get('登録を受けた都道府県名', '')
            )
            append_to_excel(excel_row)
            result = f"完全重複: {architect_name} (Excelにのみ記録)"
            
        elif office_duplicates:
            # 事務所重複: Excelにのみ追加、過去データのステータスを3に更新
            office_flag = '事務所登録重複'
            excel_row = (
                duplicate_flag,
                affiliation_flag,
                office_flag,
                office_info.get('事務所登録番号', ''),
                office_info.get('事務所所在地郵便番号', ''),
                office_info.get('事務所所在地', ''),
                office_info.get('法人名称', ''),
                office_info.get('事務所資格区分', ''),
                office_info.get('事務所名称', ''),
                office_info.get('事務所所在地ビル名等', ''),
                architect.get('建築士氏名フリガナ', ''),
                architect.get('建築士氏名', ''),
                architect.get('建築士区分', ''),
                architect.get('建築士登録番号', ''),
                architect.get('登録を受けた都道府県名', '')
            )
            append_to_excel(excel_row)
            
            # 過去の事務所重複データをステータス=3に更新
            for dup_id, dup_office_no in office_duplicates:
                cursor.execute("""
                    UPDATE 建築士情報
                    SET ステータス = 3, updated_at = %s
                    WHERE id = %s
                """, (now, dup_id))
                print(f"    🔄 過去データ更新: ID={dup_id} (事務所#{dup_office_no}) → ステータス=3")
            conn.commit()
            
            result = f"事務所重複: {architect_name} (Excelにのみ記録、過去データ更新)"
            
        elif affiliation_duplicates:
            # 所属重複: Excelにのみ追加、過去データのステータスを2に更新
            affiliation_flag = '所属重複'
            excel_row = (
                duplicate_flag,
                affiliation_flag,
                office_flag,
                office_info.get('事務所登録番号', ''),
                office_info.get('事務所所在地郵便番号', ''),
                office_info.get('事務所所在地', ''),
                office_info.get('法人名称', ''),
                office_info.get('事務所資格区分', ''),
                office_info.get('事務所名称', ''),
                office_info.get('事務所所在地ビル名等', ''),
                architect.get('建築士氏名フリガナ', ''),
                architect.get('建築士氏名', ''),
                architect.get('建築士区分', ''),
                architect.get('建築士登録番号', ''),
                architect.get('登録を受けた都道府県名', '')
            )
            append_to_excel(excel_row)
            
            # 過去の所属重複データをステータス=2に更新
            for dup_id, dup_corp, dup_office_no in affiliation_duplicates:
                cursor.execute("""
                    UPDATE 建築士情報
                    SET ステータス = 2, updated_at = %s
                    WHERE id = %s
                """, (now, dup_id))
                print(f"    🔄 過去データ更新: ID={dup_id} ({dup_corp} - 事務所#{dup_office_no}) → ステータス=2")
            conn.commit()
            
            result = f"所属重複: {architect_name} (Excelにのみ記録、過去データ更新)"
            
        else:
            # 新規登録: DBとExcelの両方に追加
            excel_row = (
                duplicate_flag,
                affiliation_flag,
                office_flag,
                office_info.get('事務所登録番号', ''),
                office_info.get('事務所所在地郵便番号', ''),
                office_info.get('事務所所在地', ''),
                office_info.get('法人名称', ''),
                office_info.get('事務所資格区分', ''),
                office_info.get('事務所名称', ''),
                office_info.get('事務所所在地ビル名等', ''),
                architect.get('建築士氏名フリガナ', ''),
                architect.get('建築士氏名', ''),
                architect.get('建築士区分', ''),
                architect.get('建築士登録番号', ''),
                architect.get('登録を受けた都道府県名', '')
            )
            
            cursor.execute("""
                INSERT INTO 建築士情報 (
                    ステータス,
                    事務所登録番号, 法人名称, 事務所資格区分,
                    事務所名称, 事務所所在地郵便番号, 事務所所在地,
                    事務所所在地ビル名等, 事務所電話番号,
                    建築士情報,
                    建築士氏名フリガナ, 建築士氏名, 建築士区分,
                    建築士登録番号, 登録を受けた都道府県名, 登録都道府県,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                0,  # ステータス=0（新規）
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
                registration_pref,
                now, now
            ))
            conn.commit()
            append_to_excel(excel_row)
            
            result = f"新規登録: {architect_name} ({architect_type})"
    
    except Error as e:
        result = f"エラー: {str(e)}"
    finally:
        cursor.close()
        conn.close()
    
    return result

def export_to_excel(filename: str = None):
    """最終統計情報を表示"""
    if filename is None:
        filename = EXCEL_FILE
        
    if os.path.exists(filename):
        wb = openpyxl.load_workbook(filename)
        ws = wb.active
        row_count = ws.max_row - 1
        
        print(f"✅ Excelファイル: {filename}")
        print(f"   - 総行数: {row_count}件")
    else:
        print(f"⚠️ Excelファイルが見つかりません: {filename}")

def insert_summary_history(office_reg_no: str, registration_pref: str, architect_count: int):
    """
    summary_historyテーブルにレコードを追加
    
    Args:
        office_reg_no: 事務所登録番号（例: "第1号"）
        registration_pref: 登録都道府県（例: "10:群馬県"）
        architect_count: 登録した建築士の総数（管理+所属）
    """
    conn = create_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    now = datetime.now()
    
    try:
        # 登録県名を抽出（例: "10:群馬県" → "群馬県"）
        pref_name = registration_pref
        if ':' in registration_pref:
            pref_name = registration_pref.split(':', 1)[1]
        
        cursor.execute("""
            INSERT INTO summary_history (
                事務所登録番号, 登録県名, 登録人数, created_at
            ) VALUES (%s, %s, %s, %s)
        """, (office_reg_no, pref_name, architect_count, now))
        
        conn.commit()
        print(f"    📊 summary_history追加: {office_reg_no} ({pref_name}) - {architect_count}人")
        
    except Error as e:
        print(f"    ⚠️ summary_history追加エラー: {str(e)}")
    finally:
        cursor.close()
        conn.close()