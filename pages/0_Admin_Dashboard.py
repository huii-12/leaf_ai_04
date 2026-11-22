import io
import json
import streamlit as st
import pandas as pd
from db_utils import (
    init_all_tables,
    get_leaf_df,
    add_bulk_leaves,
    delete_leaf_by_id,
    reset_leaf_db,
    get_outlier_logs,
    get_survey_questions,
    replace_survey_questions_from_df,
    get_all_survey_responses,
    get_all_users,
    reset_user_password,
    delete_user_account
)

init_all_tables()

if not st.session_state.get('logged_in', False) or st.session_state.get('role') != 'admin':
    st.error("⛔ 교사(관리자) 계정으로 로그인해야 접근할 수 있는 페이지입니다.")
    st.stop()

col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.title("🛠️ 교사(관리자) 통합 수업 제어 대시보드")
with col_h2:
    st.write("")
    if st.button("🔄 전체 데이터 새로고침", use_container_width=True):
        st.rerun()

st.markdown("수업 진행 단계에 맞춰 **공유 DB 초기화, 가짜 데이터 미션 투입, 엑셀 설문 문항 교체, 학생 응답·계정 관리**를 수행합니다.")

df_leaf = get_leaf_df()
df_resp = get_all_survey_responses()
df_users = get_all_users()
fake_cnt = int(df_leaf['가짜여부'].sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("등록된 학생 계정 수", f"{len(df_users[df_users['권한'] == 'student'])}명")
m2.metric("공유 DB 전체 나뭇잎 수", f"{len(df_leaf)}개")
m3.metric("현재 투입된 가짜 데이터", f"{fake_cnt}개", delta="오염 상태" if fake_cnt > 0 else "정상", delta_color="inverse")
m4.metric("윤리 설문 제출 인원", f"{len(df_resp)}명")

st.divider()

tab_db, tab_survey, tab_users = st.tabs([
    "🗄️ 1. 공유 DB 및 이상치 미션 제어",
    "📋 2. 엑셀 설문 문항 업데이트 & 학생 응답 열람",
    "👥 3. 학생 계정 및 관리자 비밀번호 관리"
])

with tab_db:
    st.subheader("🚨 수업 이벤트 트리거 (데이터 오염 방어 미션)")
    c_ev1, c_ev2, c_ev3 = st.columns(3)
    with c_ev1:
        if st.button("🚨 가짜 데이터 3개 강제 투입", type="primary", use_container_width=True):
            fake_rows = pd.DataFrame([
                {'개체명': '은행_의심1', '종': '은행', '가로': 28.5, '세로': 31.0, '잎자루': 1.2, '가짜여부': True},
                {'개체명': '화살나무_의심2', '종': '화살나무', '가로': 22.0, '세로': 4.5, '잎자루': 14.5, '가짜여부': True},
                {'개체명': '벚나무_의심3', '종': '벚나무', '가로': 2.1, '세로': 26.5, '잎자루': 13.0, '가짜여부': True},
            ])
            add_bulk_leaves(fake_rows, created_by="교사_시뮬레이션")
            st.success("⚠️ 가짜 데이터 3개가 학급 공유 DB에 투입되었습니다! 학생 화면에 즉시 경고 배너가 표시됩니다.")
            st.rerun()
    with c_ev2:
        if st.button("🧹 투입된 가짜 데이터만 일괄 제거", use_container_width=True):
            fake_ids = df_leaf[df_leaf['가짜여부']]['ID'].tolist()
            for fid in fake_ids:
                delete_leaf_by_id(fid)
            st.info(f"가짜 데이터 {len(fake_ids)}개를 모두 제거했습니다.")
            st.rerun()
    with c_ev3:
        if st.button("🔄 공유 DB 기본값(180개)으로 완전 초기화", use_container_width=True):
            reset_leaf_db()
            st.warning("공유 DB가 초기 기본 데이터셋(180개)으로 리셋되었습니다.")
            st.rerun()

    st.divider()
    col_d1, col_d2 = st.columns([1.4, 1], gap="large")
    with col_d1:
        st.markdown("**📊 현재 공유 DB 전체 레코드 (가짜여부 포함 확인)**")
        c_sort1, c_sort2 = st.columns([1.2, 1])
        with c_sort1:
            sort_col = st.selectbox(
                "정렬 기준",
                ["ID", "개체명", "종", "작성자", "가짜여부", "등록시각", "가로", "세로", "잎자루"],
                index=0,
                key="admin_db_sort_col"
            )
        with c_sort2:
            sort_dir = st.radio(
                "정렬 방향",
                ["내림차순 (최신·큰 값)", "오름차순 (1번·가나다순)"],
                index=0,
                horizontal=True,
                key="admin_db_sort_dir"
            )
        is_asc = sort_dir.startswith("오름차순")
        sorted_leaf_df = df_leaf.sort_values(by=sort_col, ascending=is_asc).reset_index(drop=True)
        st.dataframe(sorted_leaf_df, use_container_width=True, height=360)

        del_id = st.number_input("강제 삭제할 데이터 ID 입력", min_value=1, step=1)
        if st.button("선택 ID 레코드 강제 삭제"):
            delete_leaf_by_id(del_id)
            st.success(f"ID {del_id} 레코드를 삭제했습니다.")
            st.rerun()

    with col_d2:
        st.markdown("**🕵️ 학생 이상치 색출 활동 로그**")
        logs_df = get_outlier_logs()
        if len(logs_df) > 0:
            logs_df['판정'] = logs_df['실제가짜여부'].map({1: '✅ 가짜 색출 성공', 0: '⚠️ 정상 데이터 오삭제'})
            st.dataframe(logs_df[['이름', '아이디', '삭제대상', '판정', '시각']], use_container_width=True, height=360, hide_index=True)
        else:
            st.info("아직 학생들의 이상치 삭제 기록이 없습니다.")

with tab_survey:
    st.subheader("📂 엑셀(.xlsx) 파일로 설문 질문 교체")
    st.markdown("엑셀 파일에 **`질문내용`** 열(선택 열: **`윤리영역`**)을 작성해 업로드하면, **기존 문항이 모두 교체되어 업로드한 질문만 학생 화면에 표시**됩니다.")

    q_current_df = get_survey_questions()
    c_s1, c_s2 = st.columns([1, 1.5], gap="large")
    with c_s1:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            q_current_df.to_excel(writer, index=False, sheet_name='설문문항')
        st.download_button(
            label="📥 현재 설문 문항 엑셀 양식(.xlsx) 다운로드",
            data=buf.getvalue(),
            file_name="survey_questions_template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
        st.markdown("**현재 웹에 반영된 설문 문항:**")
        st.dataframe(q_current_df, use_container_width=True, height=260, hide_index=True)

    with c_s2:
        uploaded_xlsx = st.file_uploader("새 질문 엑셀 파일(.xlsx) 업로드", type=["xlsx"], key="admin_xlsx_uploader")
        if uploaded_xlsx is not None:
            try:
                new_q_df = pd.read_excel(uploaded_xlsx)
                col_rename = {}
                for c in new_q_df.columns:
                    c_str = str(c).strip()
                    if '질문' in c_str or '문항내용' in c_str or 'question' in c_str.lower():
                        col_rename[c] = '질문내용'
                    elif '영역' in c_str or 'domain' in c_str.lower() or '분류' in c_str:
                        col_rename[c] = '윤리영역'
                new_q_df = new_q_df.rename(columns=col_rename)

                if '질문내용' not in new_q_df.columns:
                    text_cols = [c for c in new_q_df.columns if new_q_df[c].dtype == object]
                    if text_cols:
                        new_q_df['질문내용'] = new_q_df[text_cols[-1]]

                if '질문내용' in new_q_df.columns:
                    valid_q = new_q_df[new_q_df['질문내용'].notna() & (new_q_df['질문내용'].astype(str).str.strip() != '')].copy()
                    st.caption(f"미리보기: 총 {len(valid_q)}개 문항 감지됨")
                    st.dataframe(valid_q[['윤리영역', '질문내용']] if '윤리영역' in valid_q.columns else valid_q[['질문내용']], use_container_width=True, height=200)
                    if st.button("✅ 이 엑셀 파일의 질문으로 학생 설문 전체 교체하기", type="primary", use_container_width=True):
                        cnt = replace_survey_questions_from_df(valid_q)
                        st.success(f"🎉 총 {cnt}개의 엑셀 질문이 학생 설문 화면에 즉시 반영되었습니다!")
                        st.rerun()
                else:
                    st.error("엑셀 파일에서 질문 텍스트 열을 찾을 수 없습니다. '질문내용' 열을 포함해 주세요.")
            except Exception as e:
                st.error(f"엑셀 파일 읽기 오류: {e}")

    st.divider()
    st.subheader("📑 전체 학생 윤리 설문 제출 결과 및 엑셀 내보내기")
    if len(df_resp) > 0:
        expanded_rows = []
        for _, r in df_resp.iterrows():
            base = {'이름': r['username'], '아이디': r['userid'], '종합평균': r['avg_score'], '제출시각': r['created_at']}
            try:
                ans = json.loads(r['answers_json'])
                base.update(ans)
            except Exception:
                pass
            expanded_rows.append(base)
        exp_df = pd.DataFrame(expanded_rows)
        st.dataframe(exp_df, use_container_width=True, hide_index=True)

        out_buf = io.BytesIO()
        with pd.ExcelWriter(out_buf, engine='openpyxl') as writer:
            exp_df.to_excel(writer, index=False, sheet_name='학생응답결과')
        st.download_button(
            label="📥 학생 설문 응답 결과 엑셀(.xlsx) 다운로드",
            data=out_buf.getvalue(),
            file_name="student_ethics_survey_results.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("아직 제출된 학생 설문 응답이 없습니다.")

with tab_users:
    st.subheader("👥 등록된 사용자 계정 목록")
    st.dataframe(df_users, use_container_width=True, hide_index=True)

    c_u1, c_u2 = st.columns(2, gap="large")
    with c_u1:
        st.markdown("**🔑 비밀번호 초기화 / 관리자 비밀번호 변경**")
        target_uid = st.selectbox("대상 아이디 선택", df_users['아이디'].tolist())
        new_pw_val = st.text_input("새 비밀번호 입력", value="1234")
        if st.button("비밀번호 변경 적용", use_container_width=True):
            if new_pw_val.strip():
                reset_user_password(target_uid, new_pw_val.strip())
                st.success(f"`{target_uid}` 계정의 비밀번호가 변경되었습니다.")
    with c_u2:
        st.markdown("**🗑️ 학생 계정 삭제**")
        student_ids = df_users[df_users['권한'] == 'student']['아이디'].tolist()
        if student_ids:
            del_uid = st.selectbox("삭제할 학생 아이디 선택", student_ids)
            if st.button("선택 학생 계정 삭제", type="secondary", use_container_width=True):
                delete_user_account(del_uid)
                st.warning(f"`{del_uid}` 계정이 삭제되었습니다.")
                st.rerun()
        else:
            st.info("삭제 가능한 학생 계정이 없습니다.")
