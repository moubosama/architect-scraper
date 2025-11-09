
### 1. パッケージインストール
```bash
pip install selenium webdriver-manager beautifulsoup4 mysql-connector-python openpyxl
```

### 2. データベース作成
```sql
CREATE DATABASE scraping_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 接続設定
`database.py`のDB_CONFIGを編集してください。

## 実行

```bash
python scraper.py
```

中断した場合は進捗から再開できます。

## 設定

`scraper.py`で変更可能：
- `START_NUMBER`: 開始番号（デフォルト: 1）
- `END_NUMBER`: 終了番号（デフォルト: 999999）
- `MAX_CONSECUTIVE_SKIPS`: 連続スキップ上限（デフォルト: 10000）

## 重複判定

### 完全重複（ステータス=1）
- 条件: 事務所登録番号 + 法人名称 + 建築士登録番号 + 氏名 + 区分が全て同じ
- 処理: DBには入れず、Excelの「重複」列にのみ記録

### 事務所重複（ステータス=3）
- 条件: 同じ法人の異なる事務所に同じ建築士がいる
- 処理: DBには入れず、Excelの「事務所登録重複」列に記録、過去データのステータスを3に更新

### 所属重複（ステータス=2）
- 条件: 異なる法人に同じ建築士がいる
- 処理: DBには入れず、Excelの「所属重複」列に記録、過去データのステータスを2に更新

### 新規（ステータス=0）
- 処理: DBとExcelの両方に保存

## 出力ファイル

### Excel: `architects_export_YYYY-MM-DD-HH.xlsx`
全データ（重複含む）が記録されます。

### MySQL: `scraping_db.建築士情報`
新規データ（ステータス=0）のみ保存されます。

### MySQL: `scraping_db.summary_history`
事務所ごとの登録人数を記録します。

## データ構造

### 建築士情報テーブル
- id, ステータス, 事務所登録番号, 法人名称, 事務所資格区分, 事務所名称
- 事務所所在地郵便番号, 事務所所在地, 事務所所在地ビル名等, 事務所電話番号
- 建築士情報, 建築士氏名フリガナ, 建築士氏名, 建築士区分
- 建築士登録番号, 登録を受けた都道府県名, 登録都道府県
- created_at, updated_at

### summary_historyテーブル
- id, 事務所登録番号, 登録県名, 登録人数, created_at
