import urllib.request
import urllib.error
import json
import platform
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import streamlit as st


# 1. 한글 글꼴 설정 함수 (운영체제별 자동 설정)
def set_korean_font():
    system_name = platform.system()
    if system_name == "Windows":
        plt.rc("font", family="Malgun Gothic")
    elif system_name == "Darwin":  # macOS
        plt.rc("font", family="AppleGothic")
    else:  # Linux (Streamlit Cloud 등)
        font_list = [f.name for f in fm.fontManager.ttflist]
        if "NanumGothic" in font_list:
            plt.rc("font", family="NanumGothic")

    # 마이너스(-) 기호 깨짐 방지
    plt.rcParams["axes.unicode_minus"] = False


# 2. NAVER API HUB 검색어 트렌드 데이터 수집 함수 (불필요한 재호출 방지를 위해 캐싱 적용)
@st.cache_data(ttl=3600)
def get_ncp_trend_data(client_id, client_secret):
    # API 인증키 확인
    if not client_id or not client_secret:
        return None, "왼쪽 사이드바에 NAVER Client ID와 Client Secret을 입력해주세요."

    url = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"
    body = {
        "startDate": "2023-08-01",
        "endDate": "2026-11-11",
        "timeUnit": "month",
        "keywordGroups": [
            {"groupName": "탕후루", "keywords": ["탕후루"]},
            {"groupName": "두쫀쿠", "keywords": ["두쫀쿠"]},
            {"groupName": "한정선", "keywords": ["한정선"]},
            {"groupName": "고디바모찌", "keywords": ["고디바모찌"]}
        ]
    }

    # API 요청 헤더 및 본문 구성
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST"
    )
    request.add_header("X-NCP-APIGW-API-KEY-ID", client_id)
    request.add_header("X-NCP-APIGW-API-KEY", client_secret)
    request.add_header("Content-Type", "application/json")

    # API 호출 및 데이터프레임 변환
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))

        df_list = [
            {"기간": item["period"], "디저트": group.get("title"), "검색량": item["ratio"]}
            for group in data.get("results", [])
            for item in group.get("data", [])
        ]

        if not df_list:
            return None, "검색 결과 데이터가 없습니다."

        df = pd.DataFrame(df_list)
        df_pivot = df.pivot(index="기간", columns="디저트", values="검색량").fillna(0)
        return df_pivot, None

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return None, f"HTTP 오류 코드: {e.code}\n상세 내용: {error_body}"
    except Exception as e:
        return None, f"오류 발생: {e}"


# 3. 기초 통계 탭 렌더링 함수
def render_stats_tab(df):
    st.subheader("수집된 실제 API 데이터 확인")

    # '통계 실행' 버튼을 눌렀을 때만 표 출력
    if st.button("통계 실행", type="primary"):
        st.dataframe(df, use_container_width=True)
        st.markdown("#### 요약 통계량")
        st.dataframe(df.describe().round(2), use_container_width=True)
    else:
        st.info("상단의 '통계 실행' 버튼을 누르면 수집된 데이터 표가 출력됩니다.")


# 4. 시각화 그래프 생성 및 출력 함수
def plot_trend_chart(df, selected_desserts, chart_type):
    set_korean_font()  # 한글 폰트 적용
    fig, ax = plt.subplots(figsize=(10, 5))

    plot_df = df[selected_desserts]

    # 선택된 그래프 종류에 따라 선 그래프 또는 막대 그래프 그리기
    if chart_type == "선 그래프 (추이 비교)":
        plot_df.plot(kind="line", marker="o", ax=ax)
        ax.set_title("디저트별 월간 검색량 추이 (선 그래프)", fontsize=14, pad=12)
    else:
        plot_df.plot(kind="bar", ax=ax, width=0.8)
        ax.set_title("디저트별 월간 검색량 비교 (막대 그래프)", fontsize=14, pad=12)

    # 축 제목 및 눈금 설정 (한글 적용)
    ax.set_xlabel("조회 기간 (월)", fontsize=11)
    ax.set_ylabel("상대 검색량 지수", fontsize=11)
    ax.legend(title="디저트 종류")
    ax.grid(True, linestyle="--", alpha=0.5)
    plt.xticks(rotation=45)
    plt.tight_layout()

    st.pyplot(fig)


# 5. 시각화 탭 렌더링 함수
def render_viz_tab(df):
    st.subheader("검색량 추이 그래프")

    # 그래프 종류 선택 (라디오 버튼)
    chart_type = st.radio(
        "그래프 종류 선택",
        ["선 그래프 (추이 비교)", "막대 그래프 (항목 비교)"],
        horizontal=True
    )

    # 디저트 항목 가로 체크박스 선택
    desserts = df.columns.tolist()
    cols = st.columns(len(desserts))
    selected_desserts = [
        dessert for col, dessert in zip(cols, desserts)
        if col.checkbox(dessert, value=True, key=f"chk_{dessert}")
    ]

    # '그래프 출력' 버튼을 눌렀을 때만 그래프 렌더링
    if st.button("그래프 출력", type="primary"):
        if selected_desserts:
            plot_trend_chart(df, selected_desserts, chart_type)
        else:
            st.warning("그래프로 볼 디저트를 1개 이상 선택해주세요.")
    else:
        st.info("옵션을 선택한 뒤 '그래프 출력' 버튼을 눌러주세요.")


# 6. 메인 앱 실행 함수
def main():
    st.set_page_config(page_title="디저트 유행 주기 분석", page_icon="🍰", layout="wide")
    st.title("디저트 유행 주기 분석 🍰")

    # 사이드바 인증키 입력
    try:
        default_id = st.secrets.get("NAVER_CLIENT_ID", "")
        default_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")
    except Exception:
        default_id, default_secret = "", ""

    st.sidebar.header("🔑 API 인증키 설정")
    input_client_id = st.sidebar.text_input("NAVER Client ID", value=default_id, type="password")
    input_client_secret = st.sidebar.text_input("NAVER Client Secret", value=default_secret, type="password")

    # 데이터 수집 호출
    df, error_msg = get_ncp_trend_data(input_client_id.strip(), input_client_secret.strip())

    if error_msg:
        st.warning(error_msg)
        return

    # 2개의 탭(기초 통계 / 시각화) 구성
    tab1, tab2 = st.tabs(["📊 기초 통계", "📈 시각화"])

    with tab1:
        render_stats_tab(df)

    with tab2:
        render_viz_tab(df)


if __name__ == "__main__":
    main()
