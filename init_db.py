import sqlite3

conn = sqlite3.connect("disaster_report.db")
c = conn.cursor()

# ==========================
# テーブル作成
# ==========================

c.execute("""
CREATE TABLE IF NOT EXISTS bases (
    base_id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_name TEXT NOT NULL,
    base_password TEXT NOT NULL,
    delete_flag INTEGER DEFAULT 0,
    delete_datetime TEXT,
    delete_by TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS companies (
    company_id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_id INTEGER NOT NULL,
    company_name TEXT NOT NULL,
    employee_count INTEGER DEFAULT 0,
    delete_flag INTEGER DEFAULT 0,
    FOREIGN KEY (base_id) REFERENCES bases(base_id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS evacuation_places (
    place_id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_id INTEGER NOT NULL,
    place_name TEXT NOT NULL,
    delete_flag INTEGER DEFAULT 0,
    FOREIGN KEY (base_id) REFERENCES bases(base_id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS reporters (
    reporter_id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_id INTEGER NOT NULL,
    reporter_name TEXT NOT NULL,
    delete_flag INTEGER DEFAULT 0,
    FOREIGN KEY (base_id) REFERENCES bases(base_id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS reports (
    report_id INTEGER PRIMARY KEY AUTOINCREMENT,
    base_id INTEGER NOT NULL,
    place_id INTEGER,
    report_date TEXT,
    report_time TEXT,
    reporter_id INTEGER,
    damage_level TEXT,
    free_comment TEXT,
    created_at TEXT,
    delete_flag INTEGER DEFAULT 0,
    delete_datetime TEXT,
    delete_by TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS report_details (
    detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    total_employee INTEGER DEFAULT 0,
    total_visitor INTEGER DEFAULT 0,
    evacuated_employee INTEGER DEFAULT 0,
    evacuated_visitor INTEGER DEFAULT 0,
    injured_employee INTEGER DEFAULT 0,
    injured_visitor INTEGER DEFAULT 0,
    absent_employee INTEGER DEFAULT 0,
    absent_visitor INTEGER DEFAULT 0,
    FOREIGN KEY (report_id) REFERENCES reports(report_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS report_images (
    image_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_id INTEGER NOT NULL,
    image_path TEXT NOT NULL,
    FOREIGN KEY (report_id) REFERENCES reports(report_id)
)
""")

conn.commit()

# ==========================
# マスタデータ投入
# ==========================

# 拠点マスタ
bases_data = [
    ("本社", "honsha2026"),
    ("東", "East2026"),
    ("中央", "center2026"),
    ("西1", "West12026"),
    ("西2", "West22026"),
    ("南1", "south12026"),
    ("南2", "south22026"),
    ("品証", "hinsyo2026"),
    ("AX", "AX2026"),
    ("AR", "AR2026"),
    ("GB", "GB2026"),
]

for name, pw in bases_data:
    c.execute("INSERT INTO bases (base_name, base_password) VALUES (?, ?)", (name, pw))

conn.commit()

# base_id を取得するための辞書
c.execute("SELECT base_id, base_name FROM bases")
base_id_map = {name: bid for bid, name in c.fetchall()}

# 会社部署マスタ
companies_data = [
    ("本社", "AH", 18),
    ("本社", "DX", 3),
    ("本社", "PJ", 3),
    ("本社", "設備", 7),
    ("本社", "営業", 6),
    ("東", "東", 20),
    ("中央", "中央", 29),
    ("西1", "西1", 44),
    ("西2", "西2", 10),
    ("南1", "南1", 21),
    ("南2", "南2", 31),
    ("品証", "品証", 10),
    ("AX", "AX", 19),
    ("AR", "AR", 7),
    ("GB", "GB", 5),
]

for base_name, company_name, emp_count in companies_data:
    c.execute(
        "INSERT INTO companies (base_id, company_name, employee_count) VALUES (?, ?, ?)",
        (base_id_map[base_name], company_name, emp_count)
    )

conn.commit()

# 避難場所マスタ
places_data = [
    ("本社", "来客駐車場"),
    ("東", "駐車場"),
    ("中央", "駐車場"),
    ("西1", "駐車場"),
    ("西2", "駐車場"),
    ("南1", "駐車場"),
    ("南2", "駐車場"),
    ("品証", "来客駐車場"),
    ("AX", "駐車場"),
    ("AR", "来客駐車場"),
    ("GB", "来客駐車場"),
]

for base_name, place_name in places_data:
    c.execute(
        "INSERT INTO evacuation_places (base_id, place_name) VALUES (?, ?)",
        (base_id_map[base_name], place_name)
    )

conn.commit()

# 報告者マスタ
reporters_data = [
    ("本社", "田中 一郎"),
    ("本社", "佐藤 次郎"),
    ("本社", "山田 すみれ"),
    ("東", "東 三太"),
    ("東", "東京 太郎"),
    ("中央", "中 史郎"),
    ("中央", "渡辺 恵子"),
    ("西1", "西 一"),
    ("西1", "西谷 順子"),
    ("西2", "太田 五郎"),
    ("西2", "西田 敏行"),
    ("南1", "南 こうせつ"),
    ("南1", "南田 八重"),
    ("南2", "難波 八郎"),
    ("南2", "中村 博"),
    ("品証", "品川 正二"),
    ("品証", "清水 由紀子"),
    ("AX", "武田 哲也"),
    ("AX", "渡 哲也"),
    ("AR", "小泉 純一郎"),
    ("AR", "羽田 孜"),
    ("GB", "高市 早苗"),
    ("GB", "田中 花子"),
]

for base_name, reporter_name in reporters_data:
    c.execute(
        "INSERT INTO reporters (base_id, reporter_name) VALUES (?, ?)",
        (base_id_map[base_name], reporter_name)
    )

conn.commit()
conn.close()

print("データベースの初期化が完了しました。")
