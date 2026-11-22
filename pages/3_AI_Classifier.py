import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.model_selection import cross_val_score
from db_utils import get_leaf_df

if not st.session_state.get('logged_in', False):
    st.warning("🔒 서비스를 이용하려면 먼저 로그인해 주세요.")
    st.stop()

col_t1, col_t2 = st.columns([4, 1])
with col_t1:
    st.title("🤖 3. 머신러닝 AI 자동 분류 및 3D 원리 시각화")
with col_t2:
    st.write("")
    if st.button("🔄 공유 DB 새로고침", use_container_width=True):
        st.rerun()

st.markdown("현재 **학급 공유 DB** 데이터를 학습시켜 새로운 나뭇잎의 종을 예측하고, **3차원 좌표 공간에서 모델이 어떻게 판단하는지(KNN 이웃 연결선 / SVM 서포트 벡터·결정 영역)** 시각적으로 확인합니다.")

df = get_leaf_df().copy()
is_fake_mask = df['가짜여부'].astype(bool).to_numpy()
fake_count = int(is_fake_mask.sum())

if fake_count > 0:
    st.error(f"🚨 주의! 현재 학급 공유 DB에 **조작된 가짜 데이터(이상치) {fake_count}개**가 포함되어 있습니다! 3D 그래프에서 가짜 데이터가 모델 판단에 어떤 영향을 주는지 확인해 보세요.")
else:
    st.success(f"✅ 현재 학급 공유 DB(총 {len(df)}개)에 조작된 데이터가 없습니다. 깨끗한 데이터셋으로 AI 모델을 학습합니다.")

col_model, col_pred = st.columns([1, 1.2], gap="large")

with col_model:
    st.subheader("⚙️ 1단계: AI 분류 알고리즘 선택 및 학습")
    algo_name = st.radio(
        "머신러닝 알고리즘 선택",
        ["KNN (K-최근접 이웃 분류기)", "SVM (서포트 벡터 머신 - 결정 경계면)"],
        help="KNN은 가장 가까운 K개 이웃과 선을 연결해 다수결로 판단하고, SVM은 클래스 사이의 경계(서포트 벡터)를 기준으로 분류합니다."
    )

    X = df[['가로', '세로', '잎자루']].to_numpy(dtype=float)
    y = df['종'].astype(str).to_numpy()

    if "KNN" in algo_name:
        max_k = max(1, min(9, len(df)))
        k_val = st.slider("이웃 개수 (K)", min_value=1, max_value=max_k, value=min(5, max_k), step=2)
        model = KNeighborsClassifier(n_neighbors=k_val)
    else:
        c_val = st.slider("규제 강도 (C)", min_value=0.1, max_value=10.0, value=1.0, step=0.1)
        model = SVC(C=c_val, kernel='rbf', probability=True, random_state=42)

    model.fit(X, y)

    clean_df = df.loc[~is_fake_mask]
    X_clean = clean_df[['가로', '세로', '잎자루']].to_numpy(dtype=float)
    y_clean = clean_df['종'].astype(str).to_numpy()

    min_class_clean = int(pd.Series(y_clean).value_counts().min()) if len(y_clean) > 0 else 0
    min_class_curr = int(pd.Series(y).value_counts().min()) if len(y) > 0 else 0

    cv_clean = min(5, min_class_clean)
    cv_curr = min(5, min_class_curr)

    clean_acc = float(cross_val_score(model, X_clean, y_clean, cv=cv_clean).mean() * 100) if cv_clean >= 2 else 0.0
    curr_acc = float(cross_val_score(model, X, y, cv=cv_curr).mean() * 100) if cv_curr >= 2 else 0.0

    m1, m2 = st.columns(2)
    m1.metric("깨끗한 DB 교차검증 정확도", f"{clean_acc:.1f}%")
    delta_val = curr_acc - clean_acc
    m2.metric("현재 공유 DB 모델 정확도", f"{curr_acc:.1f}%", delta=f"{delta_val:.1f}%" if abs(delta_val) > 0.05 else "정상")

with col_pred:
    st.subheader("🌿 2단계: 새로운 나뭇잎 특징량 입력 및 종 예측")
    st.write("새로 채집한 나뭇잎의 가로, 세로, 잎자루 길이를 입력하면 아래 **3D 공간에 ⭐(새 데이터)로 표시**됩니다.")

    c_in1, c_in2, c_in3 = st.columns(3)
    with c_in1:
        in_w = st.number_input("가로 길이 (X, cm)", min_value=0.1, max_value=50.0, value=10.4, step=0.1)
    with c_in2:
        in_l = st.number_input("세로 길이 (Y, cm)", min_value=0.1, max_value=50.0, value=6.0, step=0.1)
    with c_in3:
        in_p = st.number_input("잎자루 길이 (Z, cm)", min_value=0.0, max_value=50.0, value=5.8, step=0.1)

    sample = np.array([[float(in_w), float(in_l), float(in_p)]], dtype=float)
    pred_species = str(model.predict(sample)[0])
    probs = np.asarray(model.predict_proba(sample)[0], dtype=float)
    classes = [str(c) for c in model.classes_]

    prob_df = pd.DataFrame({
        '식물 종': classes,
        '예측 확률(%)': np.round(probs * 100, 1)
    }).sort_values(by='예측 확률(%)', ascending=False).reset_index(drop=True)
    top_conf = float(prob_df.loc[0, '예측 확률(%)'])

    if fake_count > 0:
        st.warning(f"⚠️ **AI 예측 결과: {pred_species}** (신뢰도: {top_conf}%) — *공유 DB 내 가짜 데이터({fake_count}개)로 인해 판단이 왜곡될 수 있습니다!*")
    else:
        st.success(f"🎯 **AI 예측 결과: {pred_species}** (신뢰도: {top_conf}%)")

st.divider()

# 3단계: 직관적 3차원 시각화 + 확률 막대 그래프
st.subheader("🔭 3단계: 3차원 특성 공간에서 AI 분류 원리 직관적으로 보기")

col_3d, col_bar = st.columns([1.8, 1], gap="large")

with col_3d:
    fig = go.Figure()
    palette = px.colors.qualitative.Set2
    unique_species = sorted(df['종'].unique().tolist())

    # 1) Plot existing leaf data points by species
    for idx, sp in enumerate(unique_species):
        sub = df[df['종'] == sp]
        color = palette[idx % len(palette)]
        fig.add_trace(go.Scatter3d(
            x=sub['가로'],
            y=sub['세로'],
            z=sub['잎자루'],
            mode='markers',
            name=f"{sp} ({len(sub)}개)",
            text=sub['개체명'],
            hovertemplate="<b>%{text}</b><br>종: " + sp + "<br>가로(X): %{x}<br>세로(Y): %{y}<br>잎자루(Z): %{z}<extra></extra>",
            marker=dict(size=5, color=color, opacity=0.75)
        ))

    # 2) Plot the new input leaf point as a prominent red diamond/star
    fig.add_trace(go.Scatter3d(
        x=[in_w],
        y=[in_l],
        z=[in_p],
        mode='markers+text',
        name=f"⭐ 입력 나뭇잎 (예측: {pred_species})",
        text=[f"입력값 → {pred_species}"],
        textposition="top center",
        hovertemplate=f"<b>새로운 입력 나뭇잎</b><br>예측 종: {pred_species}<br>가로(X): {in_w}<br>세로(Y): {in_l}<br>잎자루(Z): {in_p}<extra></extra>",
        marker=dict(size=11, color='#E63946', symbol='diamond', line=dict(width=2, color='black'))
    ))

    if "KNN" in algo_name:
        # Find K nearest neighbors and draw red dashed lines from input point to each neighbor!
        distances, indices = model.kneighbors(sample)
        neighbor_idxs = indices[0]
        neighbor_dists = distances[0]

        line_x, line_y, line_z = [], [], []
        neighbor_rows = []
        for rank, (n_idx, dist) in enumerate(zip(neighbor_idxs, neighbor_dists), start=1):
            row = df.iloc[int(n_idx)]
            line_x.extend([in_w, float(row['가로']), None])
            line_y.extend([in_l, float(row['세로']), None])
            line_z.extend([in_p, float(row['잎자루']), None])
            neighbor_rows.append({
                '순위': f"{rank}위",
                '이웃 개체명': row['개체명'],
                '식물 종': row['종'],
                '거리(cm)': round(float(dist), 2),
                '가짜여부': '🚨 의심데이터' if row['가짜여부'] else '정상'
            })

        # Draw connecting lines
        fig.add_trace(go.Scatter3d(
            x=line_x,
            y=line_y,
            z=line_z,
            mode='lines',
            name=f"KNN 최근접 {k_val}개 연결선",
            line=dict(color='#E63946', width=5, dash='dash'),
            hoverinfo='skip'
        ))

        # Highlight the K selected neighbor points with gold rings
        n_sub = df.iloc[neighbor_idxs]
        fig.add_trace(go.Scatter3d(
            x=n_sub['가로'],
            y=n_sub['세로'],
            z=n_sub['잎자루'],
            mode='markers',
            name=f"선택된 이웃 {k_val}개",
            text=n_sub['개체명'],
            marker=dict(size=9, color='rgba(255, 215, 0, 0.35)', line=dict(width=3, color='#FFB703')),
            hovertemplate="<b>이웃: %{text}</b><br>종: %{customdata}<extra></extra>",
            customdata=n_sub['종']
        ))

        chart_title = f"KNN (K={k_val}) 3D 시각화: 입력값(♦)과 가장 가까운 {k_val}개 이웃 연결선"
    else:
        # SVM: Highlight Support Vectors & draw translucent 3D decision grid around input point
        sv_indices = model.support_
        sv_sub = df.iloc[sv_indices]
        fig.add_trace(go.Scatter3d(
            x=sv_sub['가로'],
            y=sv_sub['세로'],
            z=sv_sub['잎자루'],
            mode='markers',
            name=f"SVM 서포트 벡터 ({len(sv_sub)}개)",
            text=sv_sub['개체명'],
            marker=dict(size=7, color='rgba(0,0,0,0)', line=dict(width=2, color='#1D3557')),
            hovertemplate="<b>서포트 벡터: %{text}</b><br>종: %{customdata}<extra></extra>",
            customdata=sv_sub['종']
        ))

        # Local 3D decision region cloud around the sample point
        span = 3.0
        grid_1d = np.linspace(-span, span, 7)
        gx, gy, gz = np.meshgrid(in_w + grid_1d, in_l + grid_1d, in_p + grid_1d)
        grid_pts = np.c_[gx.ravel(), gy.ravel(), gz.ravel()]
        grid_preds = model.predict(grid_pts)

        for idx, sp in enumerate(unique_species):
            mask_sp = (grid_preds == sp)
            if np.any(mask_sp):
                color = palette[idx % len(palette)]
                fig.add_trace(go.Scatter3d(
                    x=grid_pts[mask_sp, 0],
                    y=grid_pts[mask_sp, 1],
                    z=grid_pts[mask_sp, 2],
                    mode='markers',
                    name=f"결정영역({sp})",
                    marker=dict(size=4, color=color, opacity=0.22, symbol='square'),
                    hoverinfo='skip',
                    showlegend=False
                ))

        chart_title = f"SVM (C={c_val}) 3D 시각화: 결정 경계 영역 및 서포트 벡터(테두리 점)"

    fig.update_layout(
        title=chart_title,
        height=560,
        margin=dict(l=0, r=0, b=0, t=45),
        scene=dict(
            xaxis_title='가로 길이 X (cm)',
            yaxis_title='세로 길이 Y (cm)',
            zaxis_title='잎자루 길이 Z (cm)'
        ),
        legend=dict(itemsizing='constant')
    )
    st.plotly_chart(fig, use_container_width=True)

with col_bar:
    st.markdown("**📊 수목 종별 예측 확률 분포**")
    st.bar_chart(prob_df.set_index('식물 종'), height=260)

    if "KNN" in algo_name:
        st.markdown(f"**🔗 연결된 가장 가까운 이웃 {k_val}개 목록**")
        st.caption("붉은 점선으로 연결된 아래 이웃들의 다수결로 식물 종이 결정됩니다.")
        st.dataframe(pd.DataFrame(neighbor_rows), use_container_width=True, hide_index=True)
    else:
        st.markdown("**🧭 SVM 결정 경계면 해석 가이드**")
        st.info(
            "• **진한 테두리 점(서포트 벡터)**: 서로 다른 식물 종 군집의 최전선에서 분류 경계면을 지탱하는 핵심 데이터입니다.\n"
            "• **반투명 격자 영역**: 입력한 나뭇잎 주변 공간이 어느 종의 결정 영역에 속하는지 보여줍니다."
        )
