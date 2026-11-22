import json
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db_utils import (
    init_all_tables,
    get_survey_questions,
    save_survey_response,
    get_all_survey_responses
)

init_all_tables()

if not st.session_state.get('logged_in', False):
    st.warning("🔒 서비스를 이용하려면 먼저 로그인해 주세요.")
    st.stop()

col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.title("📝 4. AI 데이터 윤리 성찰 & 학급 역량 비교")
with col_h2:
    st.write("")
    if st.button("🔄 실시간 새로고침", use_container_width=True):
        st.rerun()

st.markdown("1~8차시 프로젝트를 통해 체득한 **데이터 윤리 의식**을 점검하고, **학급 전체 평균 레이더 차트**와 나의 윤리 역량을 비교해 봅니다.")

q_df = get_survey_questions()
st.subheader(f"📋 1단계: AI 데이터 윤리 자기점검 설문 (총 {len(q_df)}문항)")

with st.form("ethics_survey_form"):
    st.info("각 문항을 읽고 자신의 생각과 가장 가까운 점수를 선택해 주세요. (1점: 전혀 그렇지 않다 ~ 5점: 매우 그렇다)")
    answers_dict = {}
    domain_buckets = {}

    for _, row in q_df.iterrows():
        q_num = int(row['문항번호'])
        domain = str(row['윤리영역'])
        q_text = str(row['질문내용'])
        label = f"**{q_num}. [{domain}]** {q_text}"
        val = st.radio(label, [1, 2, 3, 4, 5], index=3, horizontal=True, key=f"q_radio_{q_num}")
        answers_dict[f"Q{q_num}"] = int(val)
        domain_buckets.setdefault(domain, []).append(int(val))

    submitted = st.form_submit_button("✅ 윤리 점검 결과 제출 및 학급 통계 반영", type="primary", use_container_width=True)
    if submitted:
        domain_scores = {d: round(sum(vals) / len(vals), 2) for d, vals in domain_buckets.items()}
        avg_score = round(sum(answers_dict.values()) / max(1, len(answers_dict)), 2)
        save_survey_response(
            userid=st.session_state['userid'],
            username=st.session_state['username'],
            answers_dict=answers_dict,
            domain_scores_dict=domain_scores,
            avg_score=avg_score
        )
        st.success(f"🎉 제출 완료! 나의 종합 윤리 점수는 **{avg_score} / 5.0점**입니다. 아래 레이더 차트에서 학급 평균과 비교해 보세요!")

st.divider()

st.subheader("📊 2단계: 학급 전체 AI 윤리 역량 레이더 차트 비교")
resp_df = get_all_survey_responses()

if len(resp_df) > 0:
    all_domain_records = []
    for _, r in resp_df.iterrows():
        try:
            d_map = json.loads(r['domain_scores_json'])
            all_domain_records.append(d_map)
        except Exception:
            pass

    if all_domain_records:
        all_dom_df = pd.DataFrame(all_domain_records)
        class_means = all_dom_df.mean().round(2)
        categories = class_means.index.tolist()

        my_rows = resp_df[resp_df['userid'] == st.session_state['userid']]
        if len(my_rows) > 0:
            my_latest_map = json.loads(my_rows.iloc[0]['domain_scores_json'])
            my_vals = [float(my_latest_map.get(cat, 0)) for cat in categories]
        else:
            my_vals = None

        class_vals = [float(class_means[cat]) for cat in categories]

        col_radar, col_table = st.columns([1.2, 1], gap="large")
        with col_radar:
            fig_radar = go.Figure()
            fig_radar.add_trace(go.Scatterpolar(
                r=class_vals + [class_vals[0]],
                theta=categories + [categories[0]],
                fill='toself',
                name=f'학급 전체 평균 (참여 {len(resp_df)}명)',
                line=dict(color='#1D3557', width=2),
                fillcolor='rgba(29, 53, 87, 0.2)'
            ))
            if my_vals is not None:
                fig_radar.add_trace(go.Scatterpolar(
                    r=my_vals + [my_vals[0]],
                    theta=categories + [categories[0]],
                    fill='toself',
                    name=f"나의 점수 ({st.session_state['username']})",
                    line=dict(color='#2A9D8F', width=3),
                    fillcolor='rgba(42, 157, 143, 0.25)'
                ))

            fig_radar.update_layout(
                polar=dict(radialaxis=dict(visible=True, range=[0, 5])),
                title="AI 데이터 윤리 영역별 역량 비교 (5점 만점)",
                height=440,
                margin=dict(l=40, r=40, t=50, b=30)
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with col_table:
            st.markdown("**📈 영역별 점수 요약표**")
            comp_data = {'윤리 영역': categories, '학급 평균': class_vals}
            if my_vals is not None:
                comp_data['나의 점수'] = my_vals
                comp_data['차이'] = [round(m - c, 2) for m, c in zip(my_vals, class_vals)]
            st.dataframe(pd.DataFrame(comp_data), use_container_width=True, hide_index=True)

            st.markdown("**🗂️ 최근 학급 참여 현황**")
            summary_list = resp_df[['username', 'avg_score', 'created_at']].rename(
                columns={'username': '이름', 'avg_score': '평균점수', 'created_at': '제출시각'}
            )
            st.dataframe(summary_list, use_container_width=True, height=230, hide_index=True)
else:
    st.info("아직 제출된 설문 응답이 없습니다. 위 설문을 먼저 제출하면 학급 레이더 차트가 나타납니다!")
