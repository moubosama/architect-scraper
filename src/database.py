import mysql.connector
import os
from datetime import datetime
from typing import Optional, Dict, List
import csv

def get_connection():
    """データベース接続を取得"""
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'user'),
        password=os.getenv('DB_PASS', 'password'),
        database=os.getenv('DB_NAME', 'scraping_db')
    )

def init_db():
    """テーブル作成"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS architects (
        id INT AUTO_INCREMENT PRIMARY KEY,
        -- 事務所登録情報
        office_registration_number VARCHAR(50),
        company_name VARCHAR(255),
        office_qualification VARCHAR(50),
        office_name VARCHAR(255),
        office_postal_code VARCHAR(10),
        office_address TEXT,
        office_building VARCHAR(255),
        office_phone VARCHAR(20),
        
        -- 建築士情報
        architect_name_kana VARCHAR(255),
        architect_name VARCHAR(255),
        architect_category VARCHAR(20),
        architect_registration_number VARCHAR(50),
        registration_prefecture VARCHAR(50),
        
        -- 管理建築士かどうか
        is_managing_architect BOOLEAN DEFAULT FALSE,
        
        -- 管理用
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        
        -- 重複判別用のユニークキー
        UNIQUE KEY unique_architect (
            architect_registration_number,
            architect_category,
            architect_name
        )
    )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()
    print("✅ テーブル作成完了")

def insert_or_update_architect(data: Dict) -> str:
    """
    建築士情報を挿入または更新
    重複判別: 建築士登録番号、区分、下の名前が一致したら重複
    所属会社が違う場合は更新
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # 空のデータはスキップ
        if not data.get('architect_name') or not data.get('architect_registration_number'):
            return "スキップ: 必須情報が不足"
        
        # 重複チェック
        cursor.execute("""
            SELECT id, office_registration_number, company_name 
            FROM architects 
            WHERE architect_registration_number = %s 
            AND architect_category = %s 
            AND architect_name = %s
        """, (
            data['architect_registration_number'],
            data['architect_category'],
            data['architect_name']
        ))
        
        existing = cursor.fetchone()
        
        if existing:
            # 既存レコードがある場合
            existing_id, existing_office_num, existing_company = existing
            
            # 会社が違う場合は更新
            if existing_office_num != data['office_registration_number'] or \
               existing_company != data['company_name']:
                cursor.execute("""
                    UPDATE architects SET
                        office_registration_number = %s,
                        company_name = %s,
                        office_qualification = %s,
                        office_name = %s,
                        office_postal_code = %s,
                        office_address = %s,
                        office_building = %s,
                        office_phone = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (
                    data['office_registration_number'],
                    data['company_name'],
                    data['office_qualification'],
                    data['office_name'],
                    data['office_postal_code'],
                    data['office_address'],
                    data['office_building'],
                    data['office_phone'],
                    existing_id
                ))
                conn.commit()
                return f"更新: {data['architect_name']} (ID: {existing_id})"
            else:
                return f"スキップ（重複）: {data['architect_name']}"
        else:
            # 新規挿入
            cursor.execute("""
                INSERT INTO architects (
                    office_registration_number, company_name, office_qualification,
                    office_name, office_postal_code, office_address,
                    office_building, office_phone,
                    architect_name_kana, architect_name, architect_category,
                    architect_registration_number, registration_prefecture,
                    is_managing_architect
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['office_registration_number'],
                data['company_name'],
                data['office_qualification'],
                data['office_name'],
                data['office_postal_code'],
                data['office_address'],
                data['office_building'],
                data['office_phone'],
                data['architect_name_kana'],
                data['architect_name'],
                data['architect_category'],
                data['architect_registration_number'],
                data['registration_prefecture'],
                data['is_managing_architect']
            ))
            conn.commit()
            return f"新規登録: {data['architect_name']}"
            
    except Exception as e:
        conn.rollback()
        return f"エラー: {str(e)}"
    finally:
        cursor.close()
        conn.close()

def export_to_csv(filename: str = "architects.csv"):
    """DBからCSVにエクスポート"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM architects ORDER BY id")
    rows = cursor.fetchall()
    
    # カラム名取得
    cursor.execute("SHOW COLUMNS FROM architects")
    columns = [column[0] for column in cursor.fetchall()]
    
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)
    
    cursor.close()
    conn.close()
    print(f"✅ CSVエクスポート完了: {filename} ({len(rows)}行)")

# 以前のinsert_result関数（後方互換性のため）
def insert_result(search_number: str, html: str):
    """
    旧形式の関数 - 後方互換性のため残す
    """
    print(f"⚠️ insert_result関数は非推奨です。新しいinsert_or_update_architect関数を使用してください。")
    # 何もしない（または必要に応じて実装）
    pass