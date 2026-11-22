import streamlit as st
import pandas as pd
from db_utils import (
    get_leaf_df, add_single_leaf, add_bulk_leaves, SPECIES_LIST
)

if not st.session_state.get('logged_in', False):
    st.warning("🔒 서비스를 이용하려면 먼저 로그인해 주세요.")
    st.stop()

col_title, col_sync = st.columns([4, 1])
with col_title:
    st.title("📥 1. 나뭇잎 데이터 입력 및 학급 공유 DB 구축")
with col_sync:
    st.write("")
    if st.button("🔄 실시간 새로고침", use_container_width=True):
        st.rerun()

st.markdown("모든 학생이 입력한 데이터는 **중앙 공유 데이터베이스(`myproject.db`)**에 즉시 저장되어 학급 전체 화면에 실시간으로 반영됩니다.")

df = get_leaf_df()
current_user = f"{st.session_state.get('username', '학생')}({st.session_state.get('userid', '')})"

col1, col2 = st.columns([1, 2.2], gap="large")

with col1:
    st.subheader("➕ 단일 데이터 공유 DB 입력")
    with st.form("add_leaf_form", clear_on_submit=True):
        species = st.selectbox("식물 종 (Label)", SPECIES_LIST)
        item_name = st.text_input("개체명 (선택)", placeholder="예: 1모둠_은행1")
        width = st.number_input("가로 길이 (X축, cm)", min_value=0.0, max_value=100.0, value=6.0, step=0.1)
        length = st.number_input("세로 길이 (Y축, cm)", min_value=0.0, max_value=100.0, value=8.0, step=0.1)
        petiole = st.number_input("잎자루 길이 (Z축, cm)", min_value=0.0, max_value=100.0, value=2.5, step=0.1)
        submitted = st.form_submit_button("💾 학급 공유 DB에 저장", use_container_width=True)
        if submitted:
            if not item_name.strip():
                count_sp = len(df[df['종'] == species]) + 1
                item_name = f"{species}{count_sp}"
            add_single_leaf(item_name.strip(), species, width, length, petiole, created_by=current_user, is_fake=False)
            st.success(f"✅ '{item_name}' ({species}) 데이터가 학급 공유 DB에 저장되었습니다!")
            st.rerun()

    st.divider()
    st.subheader("📁 CSV 파일 일괄 업로드")
    uploaded_file = st.file_uploader("CSV 파일 선택 (열: 종, 가로, 세로, 잎자루)", type=["csv"])
    if uploaded_file is not None:
        try:
            up_df = pd.read_csv(uploaded_file)
            col_map = {}
            for c in up_df.columns:
                if '종' in c or 'species' in c.lower():
                    col_map[c] = '종'
                elif '가로' in c or 'width' in c.lower():
                    col_map[c] = '가로'
                elif '세로' in c or 'length' in c.lower():
                    col_map[c] = '세로'
                elif '잎자루' in c or 'petiole' in c.lower():
                    col_map[c] = '잎자루'
                elif '개체' in c or 'name' in c.lower():
                    col_map[c] = '개체명'
            up_df = up_df.rename(columns=col_map)
            required = ['종', '가로', '세로', '잎자루']
            if all(r in up_df.columns for r in required):
                up_df['종'] = up_df['종'].astype(str).str.replace(r'\d+', '', regex=True).replace({'화살난무': '화살나무'})
                if '개체명' not in up_df.columns:
                    up_df['개체명'] = [f"{s}_업로드{i+1}" for i, s in enumerate(up_df['종'])]
                up_df['가짜여부'] = False
                up_df = up_df[['개체명', '종', '가로', '세로', '잎자루', '가짜여부']]
                if st.button("📥 업로드 데이터 공유 DB에 병합하기", use_container_width=True):
                    add_bulk_leaves(up_df, created_by=current_user)
                    st.success(f"🎉 {len(up_df)}개의 데이터가 학급 공유 DB에 추가되었습니다!")
                    st.rerun()
            else:
                st.error(f"필수 열({required})이 CSV 파일에 포함되어 있어야 합니다.")
        except Exception as e:
            st.error(f"CSV 파일 처리 중 오류 발생: {e}")

    st.divider()
    csv_bytes = df[['개체명', '종', '가로', '세로', '잎자루', '작성자', '등록시각']].to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📤 현재 공유 DB CSV 내려받기", data=csv_bytes, file_name="shared_leaf_db.csv", mime="text/csv", use_container_width=True)

with col2:
    st.subheader(f"📊 실시간 학급 공유 데이터베이스 현황 (총 {len(df)}개)")
    st.caption("다른 모둠 친구들이 추가한 데이터는 [🔄 실시간 새로고침] 버튼을 누르면 즉시 함께 조회됩니다.")

    counts = df['종'].value_counts()
    m_cols = st.columns(len(SPECIES_LIST))
    for idx, sp in enumerate(SPECIES_LIST):
        m_cols[idx].metric(label=sp, value=f"{counts.get(sp, 0)}개")

    display_df = df[['ID', '개체명', '종', '가로', '세로', '잎자루', '작성자', '등록시각']].iloc[::-1].reset_index(drop=True)
    st.dataframe(display_df, use_container_width=True, height=470)
