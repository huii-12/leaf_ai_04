import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from db_utils import (
    get_leaf_df, add_single_leaf, delete_leaf_by_id, log_outlier_action, SPECIES_LIST
)

if not st.session_state.get('logged_in', False):
    st.warning("🔒 서비스를 이용하려면 먼저 로그인해 주세요.")
    st.stop()

if 'deleted_leaf_history' not in st.session_state:
    st.session_state['deleted_leaf_history'] = []

col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.title("📐 2. 3차원 산점도 시각화 및 공유 DB 이상치 검증")
with col_t2:
    st.write("")
    if st.button("🔄 실시간 새로고침", use_container_width=True):
        st.rerun()

st.markdown("학급 공유 DB의 모든 데이터를 3차원 공간에 시각화하고, **수목 종별 군집 중심점(평균)**과 각 데이터까지의 **유클리드 거리**를 비교하여 조작된 이상치를 색출·정제합니다.")

df = get_leaf_df()
fake_cnt = int(df['가짜여부'].sum())
if fake_cnt > 0:
    st.error(f"🚨 긴급 미션! 현재 학급 공유 DB에 **의심스러운 이상치 데이터 {fake_cnt}개**가 감지되었습니다! 3D 그래프에서 군집 중심(◆)으로부터 유독 멀리 떨어진 점을 찾아 제거하세요!")
else:
    st.success("✅ 현재 학급 공유 DB가 깨끗한 상태입니다! 각 수종의 3차원 군집 중심점과 분포를 탐색해 보세요.")

# Calculate species centroids (mean of clean data if available, otherwise all data) and distance to own species centroid
centroids_dict = {}
for sp in SPECIES_LIST:
    sub_clean = df[(df['종'] == sp) & (~df['가짜여부'])]
    if len(sub_clean) == 0:
        sub_clean = df[df['종'] == sp]
    if len(sub_clean) > 0:
        centroids_dict[sp] = (
            float(sub_clean['가로'].mean()),
            float(sub_clean['세로'].mean()),
            float(sub_clean['잎자루'].mean())
        )
    else:
        centroids_dict[sp] = (0.0, 0.0, 0.0)

def calc_dist_to_centroid(row):
    cx, cy, cz = centroids_dict.get(row['종'], (0.0, 0.0, 0.0))
    return round(float(np.sqrt((row['가로'] - cx)**2 + (row['세로'] - cy)**2 + (row['잎자루'] - cz)**2)), 2)

df['중심점거리'] = df.apply(calc_dist_to_centroid, axis=1)

# Controls for 3D visualization & species filtering
c_opt1, c_opt2 = st.columns([1.2, 1.8])
with c_opt1:
    show_centroids = st.checkbox("🎯 수목 종별 군집 중심점(평균 ◆) 표시", value=True)
with c_opt2:
    filter_sp = st.selectbox("종 필터링 (3D 그래프 및 아래 목록 전체 연동)", ["전체"] + SPECIES_LIST)

filtered_df = df if filter_sp == "전체" else df[df['종'] == filter_sp]
filtered_rev = filtered_df.iloc[::-1].reset_index(drop=True)

options = [
    f"[ID:{row['ID']}] {row['개체명']} ({row['종']}) - 중심거리:{row['중심점거리']}cm | 가로:{row['가로']}, 세로:{row['세로']}, 잎자루:{row['잎자루']}"
    for _, row in filtered_rev.iterrows()
]

# Build 3D scatter plot — ONLY show the filtered species (or all if "전체")
palette = px.colors.qualitative.Set2
fig = go.Figure()

target_species_list = SPECIES_LIST if filter_sp == "전체" else [filter_sp]

for sp in target_species_list:
    idx = SPECIES_LIST.index(sp) if sp in SPECIES_LIST else 0
    sub = df[df['종'] == sp]
    if len(sub) == 0:
        continue
    color = palette[idx % len(palette)]
    fig.add_trace(go.Scatter3d(
        x=sub['가로'],
        y=sub['세로'],
        z=sub['잎자루'],
        mode='markers',
        name=f"{sp} ({len(sub)}개)",
        text=sub['개체명'],
        customdata=np.stack([sub['ID'], sub['중심점거리'], sub['작성자']], axis=-1),
        hovertemplate=(
            "<b>[ID:%{customdata[0]}] %{text}</b><br>"
            "종: " + sp + "<br>"
            "가로(X): %{x} cm<br>"
            "세로(Y): %{y} cm<br>"
            "잎자루(Z): %{z} cm<br>"
            "<b>중심점으로부터 거리: %{customdata[1]} cm</b><br>"
            "작성자: %{customdata[2]}<extra></extra>"
        ),
        marker=dict(size=6, color=color, opacity=0.85, line=dict(width=0.5, color='DarkSlateGrey'))
    ))

    if show_centroids and sp in centroids_dict:
        cx, cy, cz = centroids_dict[sp]
        fig.add_trace(go.Scatter3d(
            x=[cx],
            y=[cy],
            z=[cz],
            mode='markers+text',
            name=f"◆ {sp} 중심점",
            text=[f"{sp} 중심"],
            textposition="top center",
            textfont=dict(size=10, color='black'),
            hovertemplate=(
                f"<b>🎯 {sp} 군집 중심점(평균)</b><br>"
                f"중심 가로(X): {cx:.2f} cm<br>"
                f"중심 세로(Y): {cy:.2f} cm<br>"
                f"중심 잎자루(Z): {cz:.2f} cm<extra></extra>"
            ),
            marker=dict(size=9.5, color=color, symbol='diamond', line=dict(width=2.5, color='black')),
            showlegend=False
        ))

chart_title = (
    "학급 공유 DB 나뭇잎 3차원 산점도 & 종별 군집 중심점(◆)"
    if filter_sp == "전체"
    else f"[{filter_sp}] 나뭇잎 3차원 산점도 & 군집 중심점(◆)"
)

fig.update_layout(
    title=chart_title,
    height=560,
    margin=dict(l=0, r=0, b=0, t=40),
    scene=dict(
        xaxis_title='가로 길이 X (cm)',
        yaxis_title='세로 길이 Y (cm)',
        zaxis_title='잎자루 길이 Z (cm)'
    )
)
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("🔍 이상치(조작된 데이터) 거리 비교 · 색출 · 되돌리기")
st.write("각 종의 **군집 중심점(평균 좌표)**과 **중심점으로부터의 정상 거리 범위**를 참고하여 이상치를 선택·삭제하세요. 잘못 삭제한 경우 바로 되돌릴 수 있습니다.")

col_stat, col_del = st.columns([1.45, 1], gap="large")

with col_stat:
    st.markdown("**📌 수목 종별 정상 범위 참고 (군집 중심점 · 최소 · 최대 · 중심 거리)**")
    clean_only = df[~df['가짜여부']]
    stat_rows = []
    for sp in target_species_list:
        sub_c = clean_only[clean_only['종'] == sp]
        if len(sub_c) > 0:
            cx, cy, cz = centroids_dict[sp]
            stat_rows.append({
                '종': sp,
                '중심점(가로,세로,잎자루)': f"({cx:.1f}, {cy:.1f}, {cz:.1f})",
                '정상 중심거리(평균/최대)': f"{sub_c['중심점거리'].mean():.2f} / {sub_c['중심점거리'].max():.2f} cm",
                '가로(최소~최대)': f"{sub_c['가로'].min():.1f}~{sub_c['가로'].max():.1f}",
                '세로(최소~최대)': f"{sub_c['세로'].min():.1f}~{sub_c['세로'].max():.1f}",
                '잎자루(최소~최대)': f"{sub_c['잎자루'].min():.1f}~{sub_c['잎자루'].max():.1f}",
            })
    st.dataframe(pd.DataFrame(stat_rows), use_container_width=True, hide_index=True)

    st.markdown("**📏 나뭇잎별 중심점 거리 순위 (거리가 클수록 이상치 의심)**")
    dist_table = filtered_df[['ID', '개체명', '종', '중심점거리', '가로', '세로', '잎자루', '작성자']].sort_values(
        by='중심점거리', ascending=False
    ).reset_index(drop=True)
    st.dataframe(dist_table, use_container_width=True, height=230, hide_index=True)

with col_del:
    st.markdown("**🗑️ 의심 데이터 선택 및 공유 DB에서 제거**")
    selected_option = st.selectbox(
        "삭제할 데이터 항목 선택 (최신 등록순)",
        options,
        key="selected_outlier_opt"
    )

    if st.button("🗑️ 선택한 데이터 삭제하기", type="primary", use_container_width=True):
        if selected_option:
            target_id = int(selected_option.split(']')[0].replace('[ID:', ''))
            target_row = df[df['ID'] == target_id].iloc[0]
            is_fake_target = bool(target_row['가짜여부'])
            target_name = target_row['개체명']

            st.session_state['deleted_leaf_history'].append({
                '개체명': str(target_row['개체명']),
                '종': str(target_row['종']),
                '가로': float(target_row['가로']),
                '세로': float(target_row['세로']),
                '잎자루': float(target_row['잎자루']),
                '가짜여부': is_fake_target,
                '작성자': str(target_row['작성자'])
            })

            delete_leaf_by_id(target_id)
            log_outlier_action(
                userid=st.session_state.get('userid', ''),
                username=st.session_state.get('username', ''),
                target_name=target_name,
                is_true_fake=is_fake_target
            )
            if is_fake_target:
                st.success(f"🎉 정답입니다! 조작된 가짜 데이터 '{target_name}'을(를) 공유 DB에서 정확히 색출하여 제거했습니다!")
                st.balloons()
            else:
                st.warning(f"⚠️ '{target_name}' 데이터는 정상 데이터였습니다. 아래 [↩️ 방금 삭제 항목 복구] 버튼으로 되돌릴 수 있습니다!")
            st.rerun()

    st.divider()
    st.markdown("**↩️ 삭제한 데이터 되돌리기 (복구)**")
    history = st.session_state['deleted_leaf_history']
    if len(history) > 0:
        last_item = history[-1]
        st.caption(f"최근 삭제 항목: **{last_item['개체명']}** ({last_item['종']} | 가로:{last_item['가로']}, 세로:{last_item['세로']}, 잎자루:{last_item['잎자루']})")
        c_undo1, c_undo2 = st.columns(2)
        with c_undo1:
            if st.button("↩️ 방금 삭제 항목 복구", use_container_width=True):
                restored = st.session_state['deleted_leaf_history'].pop()
                add_single_leaf(
                    item_name=restored['개체명'],
                    species=restored['종'],
                    width=restored['가로'],
                    length=restored['세로'],
                    petiole=restored['잎자루'],
                    created_by=restored['작성자'],
                    is_fake=restored['가짜여부']
                )
                st.success(f"✅ '{restored['개체명']}' 데이터가 공유 DB에 다시 복구되었습니다!")
                st.rerun()
        with c_undo2:
            if st.button(f"🔄 삭제 내역 전체 복구 ({len(history)}개)", use_container_width=True):
                cnt_restored = len(st.session_state['deleted_leaf_history'])
                while st.session_state['deleted_leaf_history']:
                    item = st.session_state['deleted_leaf_history'].pop()
                    add_single_leaf(
                        item_name=item['개체명'],
                        species=item['종'],
                        width=item['가로'],
                        length=item['세로'],
                        petiole=item['잎자루'],
                        created_by=item['작성자'],
                        is_fake=item['가짜여부']
                    )
                st.success(f"✅ 삭제했던 {cnt_restored}개의 데이터가 모두 공유 DB에 복구되었습니다!")
                st.rerun()
    else:
        st.caption("현재 세션에서 삭제한 데이터 내역이 없습니다.")
