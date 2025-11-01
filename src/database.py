import mysql.connector
from mysql.connector import Error
import openpyxl
from openpyxl.styles import Font
from datetime import datetime

# MySQL接続情報
# XAMPPを使用している場合、通常はパスワードなしです
DB_CONFIG = {
    'host': '127.0.0.1',  # localhostの代わりに127.0.0.1を使用
    'port': 3306,
    'user': 'root',
    'password': 'root',  # XAMPPのデフォルトは空白。パスワードがあれば入力してください
    'database': 'scraping_db'
}

def create_connection():
    """MySQL接続を作成"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"❌ MySQL接続エラー: {e}")
        return None

def init_db():
    """データベースとテーブルを初期化"""
    conn = create_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # 建築士情報テーブル（1行 = 事務所 + 建築士1人）
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
        UNIQUE KEY unique_architect (建築士登録番号, 建築士区分, 建築士氏名)
    ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ データベースを初期化しました（MySQL）")

def insert_architect_row(office_info: dict, architect: dict, architect_type: str) -> str:
    """
    建築士情報を1行としてDBに挿入または更新
    
    Args:
        office_info: 事務所情報
        architect: 建築士情報（管理 or 所属）
        architect_type: "管理建築士情報" or "所属建築士情報"
    """
    conn = create_connection()
    if not conn:
        return "接続エラー"
    
    cursor = conn.cursor()
    now = datetime.now()
    
    try:
        # 重複チェック
        cursor.execute("""
            SELECT id, 事務所名称, 法人名称 FROM 建築士情報
            WHERE 建築士登録番号 = %s 
            AND 建築士区分 = %s
            AND 建築士氏名 = %s
        """, (
            architect.get('建築士登録番号', ''),
            architect.get('建築士区分', ''),
            architect.get('建築士氏名', '')
        ))
        
        existing = cursor.fetchone()
        
        if existing:
            existing_id = existing[0]
            existing_office = existing[1]
            existing_company = existing[2]
            
            new_office = office_info.get('事務所名称', '')
            new_company = office_info.get('法人名称', '')
            
            # 会社が変わっていたら更新
            if existing_office != new_office or existing_company != new_company:
                cursor.execute("""
                    UPDATE 建築士情報 SET
                        事務所登録番号 = %s,
                        法人名称 = %s,
                        事務所資格区分 = %s,
                        事務所名称 = %s,
                        事務所所在地郵便番号 = %s,
                        事務所所在地 = %s,
                        事務所所在地ビル名等 = %s,
                        事務所電話番号 = %s,
                        建築士情報 = %s,
                        updated_at = %s
                    WHERE id = %s
                """, (
                    office_info.get('事務所登録番号', ''),
                    new_company,
                    office_info.get('事務所資格区分', ''),
                    new_office,
                    office_info.get('事務所所在地郵便番号', ''),
                    office_info.get('事務所所在地', ''),
                    office_info.get('事務所所在地ビル名等', ''),
                    office_info.get('事務所電話番号', ''),
                    architect_type,
                    now,
                    existing_id
                ))
                conn.commit()
                result = f"更新: {architect.get('建築士氏名')} (会社変更)"
            else:
                result = f"スキップ: {architect.get('建築士氏名')}"
        else:
            # 新規登録
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
                '',  # 重複（後で実装）
                office_info.get('事務所登録番号', ''),
                office_info.get('法人名称', ''),
                office_info.get('事務所資格区分', ''),
                office_info.get('事務所名称', ''),
                office_info.get('事務所所在地郵便番号', ''),
                office_info.get('事務所所在地', ''),
                office_info.get('事務所所在地ビル名等', ''),
                office_info.get('事務所電話番号', ''),
                architect_type,  # "管理建築士情報" or "所属建築士情報"
                architect.get('建築士氏名フリガナ', ''),
                architect.get('建築士氏名', ''),
                architect.get('建築士区分', ''),
                architect.get('建築士登録番号', ''),
                architect.get('登録を受けた都道府県名', ''),
                now, now
            ))
            conn.commit()
            result = f"新規登録: {architect.get('建築士氏名')} ({architect_type})"
    
    except Error as e:
        result = f"エラー: {str(e)}"
    finally:
        cursor.close()
        conn.close()
    
    return result

def export_to_excel(filename: str = "architects_export.xlsx"):
    """データベースの内容を1シートのExcelにエクスポート"""
    conn = create_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    
    # Excelワークブック作成
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "建築士情報"
    
    # created_at順でソート（取得順）
    cursor.execute("""
        SELECT 
            重複,
            事務所登録番号, 法人名称, 事務所資格区分, 事務所名称,
            事務所所在地郵便番号, 事務所所在地, 事務所所在地ビル名等, 事務所電話番号,
            建築士情報,
            建築士氏名フリガナ, 建築士氏名, 建築士区分,
            建築士登録番号, 登録を受けた都道府県名
        FROM 建築士情報 
        ORDER BY created_at
    """)
    rows = cursor.fetchall()
    
    # カラム名
    columns = [
        '重複',
        '事務所登録番号', '法人名称', '事務所資格区分', '事務所名称',
        '事務所所在地郵便番号', '事務所所在地', '事務所所在地ビル名等', '事務所電話番号',
        '建築士情報',
        '建築士氏名フリガナ', '建築士氏名', '建築士区分',
        '建築士登録番号', '登録を受けた都道府県名'
    ]
    
    ws.append(columns)
    for row in rows:
        ws.append(row)
    
    # ヘッダーを太字に
    for cell in ws[1]:
        cell.font = Font(bold=True)
    
    # Excelファイル保存
    wb.save(filename)
    cursor.close()
    conn.close()
    
    print(f"✅ Excelエクスポート完了:")
    print(f"   - 建築士情報: {len(rows)}件")
    print(f"   ファイル名: {filename}")