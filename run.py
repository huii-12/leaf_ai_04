import streamlit as st
import pytz
from datetime import datetime
import sqlite3
from db_utils import get_conn, init_all_tables

st.set_page_config(
    page_title="AI 나뭇잎 분류 & 윤리 시뮬레이터",
    page_icon="🌱",
    layout="wide",
    initial_sidebar_state="expanded"
)

init_all_tables()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'userid' not in st.session_state:
    st.session_state['userid'] = None
if 'username' not in st.session_state:
    st.session_state['username'] = None
if 'role' not in st.session_state:
    st.session_state['role'] = None


def auth_landing_page():
    st.title("🌱 AI 나뭇잎 분류 & 윤리 시뮬레이터")
    st.write("학급 실시간 공유 데이터베이스(`myproject.db`) 기반 머신러닝 분류 및 데이터 윤리 학습 플랫폼입니다.")

    tab_student, tab_signup, tab_admin = st.tabs(["🧑‍🎓 학생 로그인", "📝 학생 회원가입", "👨‍🏫 교사(관리자) 로그인"])

    with tab_student:
        st.subheader("학생 로그인")
        with st.form("student_login_form"):
            login_id = st.text_input("학생 아이디")
            login_pw = st.text_input("비밀번호", type="password")
            submit_login = st.form_submit_button("학생 로그인", type="primary")

            if submit_login:
                if login_id and login_pw:
                    conn = get_conn()
                    c = conn.cursor()
                    c.execute("SELECT username, role FROM users WHERE userid=? AND passwd=?", (login_id, login_pw))
                    result = c.fetchone()
                    conn.close()

                    if result:
                        st.session_state['logged_in'] = True
                        st.session_state['userid'] = login_id
                        st.session_state['username'] = result[0]
                        st.session_state['role'] = result[1]
                        st.rerun()
                    else:
                        st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
                else:
                    st.warning("아이디와 비밀번호를 모두 입력해 주세요.")

    with tab_signup:
        st.subheader("신규 학생 회원가입")
        with st.form("signup_form"):
            reg_name = st.text_input("이름 (예: 1모둠 홍길동)")
            reg_id = st.text_input("아이디")
            reg_pw = st.text_input("비밀번호", type="password")
            reg_pw2 = st.text_input("비밀번호 확인", type="password")
            submit_signup = st.form_submit_button("가입하기")

            if submit_signup:
                if not reg_name or not reg_id or not reg_pw:
                    st.warning("모든 항목을 입력해 주세요.")
                elif reg_pw != reg_pw2:
                    st.warning("비밀번호가 일치하지 않습니다.")
                else:
                    try:
                        conn = get_conn()
                        c = conn.cursor()
                        kst = pytz.timezone('Asia/Seoul')
                        now = datetime.now(kst).strftime('%Y-%m-%d %H:%M:%S')
                        c.execute(
                            "INSERT INTO users (username, userid, passwd, role, created_at) VALUES (?, ?, ?, 'student', ?)",
                            (reg_name, reg_id, reg_pw, now)
                        )
                        conn.commit()
                        conn.close()
                        st.success("학생 회원가입이 완료되었습니다. [🧑‍🎓 학생 로그인] 탭에서 로그인해 주세요.")
                    except sqlite3.IntegrityError:
                        st.error("이미 존재하는 아이디입니다.")

    with tab_admin:
        st.subheader("교사(관리자) 전용 로그인")
        st.info("기본 관리자 계정 — 아이디: `admin` / 초기 비밀번호: `admin1234` (로그인 후 관리자 대시보드에서 변경 가능)")
        with st.form("admin_login_form"):
            admin_id = st.text_input("관리자 아이디", value="admin")
            admin_pw = st.text_input("관리자 비밀번호", type="password")
            submit_admin = st.form_submit_button("관리자 대시보드 입장", type="primary")

            if submit_admin:
                conn = get_conn()
                c = conn.cursor()
                c.execute("SELECT username, role FROM users WHERE userid=? AND passwd=? AND role='admin'", (admin_id, admin_pw))
                res = c.fetchone()
                conn.close()
                if res:
                    st.session_state['logged_in'] = True
                    st.session_state['userid'] = admin_id
                    st.session_state['username'] = res[0]
                    st.session_state['role'] = 'admin'
                    st.rerun()
                else:
                    st.error("관리자 인증에 실패했습니다. 아이디와 비밀번호를 확인해 주세요.")


def student_home_page():
    st.title("🌱 AI 나뭇잎 분류 & 윤리 학습 홈")
    st.write(f"**{st.session_state['username']}**님, 환영합니다! 🎉")
    st.write("왼쪽 사이드바 또는 아래 단계별 카드를 눌러 수업 활동을 진행해 주세요.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.page_link("pages/1_Data_Input.py", label="1. 공유 DB 데이터 입력", icon="📥", use_container_width=True)
    with c2:
        st.page_link("pages/2_3D_Outlier_Check.py", label="2. 3D 산점도 & 이상치 검증", icon="📐", use_container_width=True)
    with c3:
        st.page_link("pages/3_AI_Classifier.py", label="3. AI 자동 분류 & 3D 시각화", icon="🤖", use_container_width=True)
    with c4:
        st.page_link("pages/4_Ethics_Survey.py", label="4. AI 윤리 성찰 & 학급 비교", icon="📝", use_container_width=True)


if not st.session_state['logged_in']:
    pg = st.navigation([st.Page(auth_landing_page, title="로그인 / 회원가입", icon="🔐")], position="hidden")
    pg.run()
else:
    if st.session_state['role'] == 'admin':
        page_admin = st.Page("pages/0_Admin_Dashboard.py", title="관리자 통합 대시보드", icon="🛠️", default=True)
        page_1 = st.Page("pages/1_Data_Input.py", title="1. 공유 DB 데이터 입력", icon="📥")
        page_2 = st.Page("pages/2_3D_Outlier_Check.py", title="2. 3D 산점도 & 이상치 검증", icon="📐")
        page_3 = st.Page("pages/3_AI_Classifier.py", title="3. AI 자동 분류 & 3D 시각화", icon="🤖")
        page_4 = st.Page("pages/4_Ethics_Survey.py", title="4. AI 윤리 성찰 & 학급 비교", icon="📝")

        pages = {
            "👨‍🏫 교사(관리자) 제어실": [page_admin],
            "🧑‍🎓 학생 화면 미리보기": [page_1, page_2, page_3, page_4]
        }
        pg = st.navigation(pages, position="hidden")

        with st.sidebar:
            st.success(f"👨‍🏫 교사(관리자) | **{st.session_state['username']}**")
            st.markdown("### 🧭 메뉴 바로가기")
            st.page_link(page_admin, label="관리자 통합 대시보드", icon="🛠️")
            st.page_link(page_1, label="1. 공유 DB 데이터 입력", icon="📥")
            st.page_link(page_2, label="2. 3D 산점도 & 이상치 검증", icon="📐")
            st.page_link(page_3, label="3. AI 자동 분류 & 3D 시각화", icon="🤖")
            st.page_link(page_4, label="4. AI 윤리 성찰 & 학급 비교", icon="📝")
            st.divider()
            if st.button("🚪 로그아웃", use_container_width=True):
                st.session_state['logged_in'] = False
                st.session_state['userid'] = None
                st.session_state['username'] = None
                st.session_state['role'] = None
                st.rerun()
        pg.run()
    else:
        page_home = st.Page(student_home_page, title="학습 홈", icon="🏠", default=True)
        page_1 = st.Page("pages/1_Data_Input.py", title="1. 공유 DB 데이터 입력", icon="📥")
        page_2 = st.Page("pages/2_3D_Outlier_Check.py", title="2. 3D 산점도 & 이상치 검증", icon="📐")
        page_3 = st.Page("pages/3_AI_Classifier.py", title="3. AI 자동 분류 & 3D 시각화", icon="🤖")
        page_4 = st.Page("pages/4_Ethics_Survey.py", title="4. AI 윤리 성찰 & 학급 비교", icon="📝")

        pages = {
            "🌱 학습 활동 메뉴": [page_home, page_1, page_2, page_3, page_4]
        }
        pg = st.navigation(pages, position="hidden")

        with st.sidebar:
            st.success(f"🧑‍🎓 학생 | **{st.session_state['username']}**")
            st.markdown("### 🌱 학습 메뉴")
            st.page_link(page_home, label="학습 홈", icon="🏠")
            st.page_link(page_1, label="1. 공유 DB 데이터 입력", icon="📥")
            st.page_link(page_2, label="2. 3D 산점도 & 이상치 검증", icon="📐")
            st.page_link(page_3, label="3. AI 자동 분류 & 3D 시각화", icon="🤖")
            st.page_link(page_4, label="4. AI 윤리 성찰 & 학급 비교", icon="📝")
            st.divider()
            if st.button("🚪 로그아웃", use_container_width=True):
                st.session_state['logged_in'] = False
                st.session_state['userid'] = None
                st.session_state['username'] = None
                st.session_state['role'] = None
                st.rerun()
        pg.run()
