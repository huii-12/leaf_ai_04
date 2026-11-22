import os
import json
import sqlite3
import pytz
from datetime import datetime
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'myproject.db')
DEFAULT_CSV_PATH = os.path.join(BASE_DIR, 'data', 'leaf_data.csv')
DEFAULT_SURVEY_XLSX = os.path.join(BASE_DIR, 'data', 'survey_questions.xlsx')

SPECIES_LIST = ['은행', '단풍', '벚나무', '감나무', '밤나무', '화살나무']

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_all_tables():
    conn = get_conn()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                    id_num INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    username TEXT NOT NULL,
                    userid TEXT UNIQUE NOT NULL,
                    passwd TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'student',
                    created_at TEXT NOT NULL)''')

    c.execute("PRAGMA table_info(users)")
    cols = [row[1] for row in c.fetchall()]
    if 'role' not in cols:
        c.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'student'")

    c.execute("SELECT COUNT(*) FROM users WHERE userid = 'admin'")
    if c.fetchone()[0] == 0:
        kst = pytz.timezone('Asia/Seoul')
        now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
        c.execute(
            "INSERT INTO users (username, userid, passwd, role, created_at) VALUES (?, ?, ?, ?, ?)",
            ('선생님(관리자)', 'admin', 'admin1234', 'admin', now)
        )
    else:
        c.execute("UPDATE users SET role = 'admin' WHERE userid = 'admin'")

    c.execute('''CREATE TABLE IF NOT EXISTS inventory (
                    id_num INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    userid TEXT NOT NULL,
                    q1 INTEGER, q2 INTEGER, q3 INTEGER, q4 INTEGER, q5 INTEGER,
                    q6 INTEGER, q7 INTEGER, q8 INTEGER, q9 INTEGER, q10 INTEGER,
                    created_at TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS leaf_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    item_name TEXT NOT NULL,
                    species TEXT NOT NULL,
                    width REAL NOT NULL,
                    length REAL NOT NULL,
                    petiole REAL NOT NULL,
                    is_fake INTEGER NOT NULL DEFAULT 0,
                    created_by TEXT NOT NULL DEFAULT '기본데이터',
                    created_at TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS survey_questions (
                    q_num INTEGER PRIMARY KEY NOT NULL,
                    domain TEXT NOT NULL,
                    question_text TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS survey_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    userid TEXT NOT NULL,
                    username TEXT NOT NULL,
                    answers_json TEXT NOT NULL,
                    domain_scores_json TEXT NOT NULL,
                    avg_score REAL NOT NULL,
                    created_at TEXT NOT NULL
                )''')
    c.execute('''CREATE TABLE IF NOT EXISTS outlier_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                    userid TEXT NOT NULL,
                    username TEXT NOT NULL,
                    target_name TEXT NOT NULL,
                    is_true_fake INTEGER NOT NULL,
                    created_at TEXT NOT NULL
                )''')

    c.execute("SELECT COUNT(*) FROM leaf_records")
    if c.fetchone()[0] == 0:
        _seed_default_data(c)

    c.execute("SELECT COUNT(*) FROM survey_questions")
    if c.fetchone()[0] == 0:
        _seed_default_questions(c)

    conn.commit()
    conn.close()

def _seed_default_data(cursor):
    df = pd.read_csv(DEFAULT_CSV_PATH)
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
    rows = []
    for _, r in df.iterrows():
        rows.append((
            str(r['개체명']),
            str(r['종']),
            float(r['가로']),
            float(r['세로']),
            float(r['잎자루']),
            int(bool(r['가짜여부'])),
            '기본데이터',
            now
        ))
    cursor.executemany(
        "INSERT INTO leaf_records (item_name, species, width, length, petiole, is_fake, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows
    )

def _seed_default_questions(cursor):
    if os.path.exists(DEFAULT_SURVEY_XLSX):
        q_df = pd.read_excel(DEFAULT_SURVEY_XLSX)
        rows = []
        for idx, r in q_df.iterrows():
            q_num = int(r.get('문항번호', idx + 1)) if pd.notna(r.get('문항번호', idx + 1)) else idx + 1
            domain = str(r.get('윤리영역', '데이터윤리')).strip() if pd.notna(r.get('윤리영역', '데이터윤리')) else '데이터윤리'
            q_text = str(r['질문내용']).strip()
            if q_text and q_text.lower() != 'nan':
                rows.append((q_num, domain, q_text))
        if rows:
            cursor.executemany(
                "INSERT INTO survey_questions (q_num, domain, question_text) VALUES (?, ?, ?)",
                rows
            )

def get_all_users():
    init_all_tables()
    conn = get_conn()
    df = pd.read_sql_query("SELECT id_num AS 번호, username AS 이름, userid AS 아이디, role AS 권한, created_at AS 가입일시 FROM users ORDER BY id_num ASC", conn)
    conn.close()
    return df

def reset_user_password(userid, new_pw="1234"):
    init_all_tables()
    conn = get_conn()
    c = conn.cursor()
    c.execute("UPDATE users SET passwd = ? WHERE userid = ?", (new_pw, userid))
    conn.commit()
    conn.close()

def delete_user_account(userid):
    if userid == 'admin':
        return
    init_all_tables()
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE userid = ?", (userid,))
    conn.commit()
    conn.close()

def log_outlier_action(userid, username, target_name, is_true_fake):
    init_all_tables()
    conn = get_conn()
    c = conn.cursor()
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
    c.execute(
        "INSERT INTO outlier_logs (userid, username, target_name, is_true_fake, created_at) VALUES (?, ?, ?, ?, ?)",
        (userid, username, target_name, int(bool(is_true_fake)), now)
    )
    conn.commit()
    conn.close()

def get_outlier_logs():
    init_all_tables()
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT id AS 번호, username AS 이름, userid AS 아이디, target_name AS 삭제대상, is_true_fake AS 실제가짜여부, created_at AS 시각 FROM outlier_logs ORDER BY id DESC",
        conn
    )
    conn.close()
    return df

def get_survey_questions():
    init_all_tables()
    conn = get_conn()
    df = pd.read_sql_query("SELECT q_num AS 문항번호, domain AS 윤리영역, question_text AS 질문내용 FROM survey_questions ORDER BY q_num ASC", conn)
    conn.close()
    return df

def replace_survey_questions_from_df(q_df):
    init_all_tables()
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM survey_questions")
    rows = []
    for idx, r in q_df.iterrows():
        q_num = idx + 1
        domain = str(r['윤리영역']).strip() if '윤리영역' in q_df.columns and pd.notna(r['윤리영역']) and str(r['윤리영역']).strip() != '' else '데이터윤리'
        q_text = str(r['질문내용']).strip()
        if q_text and q_text.lower() != 'nan':
            rows.append((q_num, domain, q_text))
    c.executemany("INSERT INTO survey_questions (q_num, domain, question_text) VALUES (?, ?, ?)", rows)
    conn.commit()
    conn.close()
    return len(rows)

def save_survey_response(userid, username, answers_dict, domain_scores_dict, avg_score):
    init_all_tables()
    conn = get_conn()
    c = conn.cursor()
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
    c.execute(
        "INSERT INTO survey_responses (userid, username, answers_json, domain_scores_json, avg_score, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (userid, username, json.dumps(answers_dict, ensure_ascii=False), json.dumps(domain_scores_dict, ensure_ascii=False), float(avg_score), now)
    )
    q_vals = [int(answers_dict.get(f"Q{i}", 0)) for i in range(1, 11)]
    c.execute(
        "INSERT INTO inventory (userid, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (userid, *q_vals, now)
    )
    conn.commit()
    conn.close()

def get_all_survey_responses():
    init_all_tables()
    conn = get_conn()
    df = pd.read_sql_query(
        "SELECT id, userid, username, answers_json, domain_scores_json, avg_score, created_at FROM survey_responses ORDER BY id DESC",
        conn
    )
    conn.close()
    return df

def get_leaf_df():
    init_all_tables()
    conn = get_conn()
    df = pd.read_sql_query(
        '''SELECT id AS ID,
                  item_name AS 개체명,
                  species AS 종,
                  width AS 가로,
                  length AS 세로,
                  petiole AS 잎자루,
                  is_fake AS 가짜여부,
                  created_by AS 작성자,
                  created_at AS 등록시각
           FROM leaf_records
           ORDER BY id ASC''',
        conn
    )
    conn.close()
    df['가짜여부'] = df['가짜여부'].apply(lambda v: bool(int.from_bytes(v, 'little')) if isinstance(v, (bytes, bytearray)) else bool(int(v)))
    return df

def add_single_leaf(item_name, species, width, length, petiole, created_by, is_fake=False):
    init_all_tables()
    conn = get_conn()
    c = conn.cursor()
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
    c.execute(
        "INSERT INTO leaf_records (item_name, species, width, length, petiole, is_fake, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (item_name, species, float(width), float(length), float(petiole), int(bool(is_fake)), created_by, now)
    )
    conn.commit()
    conn.close()

def add_bulk_leaves(records_df, created_by):
    init_all_tables()
    conn = get_conn()
    c = conn.cursor()
    kst = pytz.timezone('Asia/Seoul')
    now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
    rows = []
    for _, r in records_df.iterrows():
        rows.append((
            str(r['개체명']),
            str(r['종']),
            float(r['가로']),
            float(r['세로']),
            float(r['잎자루']),
            int(bool(r['가짜여부'])),
            created_by,
            now
        ))
    c.executemany(
        "INSERT INTO leaf_records (item_name, species, width, length, petiole, is_fake, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        rows
    )
    conn.commit()
    conn.close()

def delete_leaf_by_id(record_id):
    init_all_tables()
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM leaf_records WHERE id = ?", (int(record_id),))
    conn.commit()
    conn.close()

def reset_leaf_db():
    init_all_tables()
    conn = get_conn()
    c = conn.cursor()
    c.execute("DELETE FROM leaf_records")
    c.execute("DELETE FROM sqlite_sequence WHERE name='leaf_records'")
    _seed_default_data(c)
    conn.commit()
    conn.close()
