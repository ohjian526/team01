import urllib.request
import urllib.error
import json
import pandas as pd
import streamlit as st


def get_ncp_trend_data(client_id, client_secret):

    # 1. API 인증키 확인
    if not client_id or not client_secret:
        st.warning("왼쪽 사이드바에 NAVER Client ID와 Client Secret을 입력해주세요.")
        return None

    # 2. NAVER API HUB 검색어 트렌드 주소
    url = "https://naverapihub.apigw.ntruss.com/search-trend/v1/search"

    # 3. 검색어 및 조회 기간 설정
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

    # 4. API 요청 설정
    request = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        method="POST"
    )

    request.add_header(
        "X-NCP-APIGW-API-KEY-ID",
        client_id
    )

    request.add_header(
        "X-NCP-APIGW-API-KEY",
        client_secret
    )

    request.add_header(
        "Content-Type",
        "application/json"
    )

    # 5. API 호출 및 데이터 수집
    try:
        with urllib.request.urlopen(request, timeout=30) as response:

            response_body = response.read().decode("utf-8")
            data = json.loads(response_body)

        # 6. 검색 결과 정리
        df_list = []

        for group in data.get("results", []):

            title = group.get("title")

            for item in group.get("data", []):

                df_list.append({
                    "기간": item["period"],
                    "디저트": title,
                    "검색량": item["ratio"]
                })

        # 7. 데이터프레임 생성
        if not df_list:
            st.warning("검색 결과 데이터가 없습니다.")
            return None

        df = pd.DataFrame(df_list)

        df_pivot = df.pivot(
            index="기간",
            columns="디저트",
            values="검색량"
        ).fillna(0)

        return df_pivot

    # 8. 오류 처리
    except urllib.error.HTTPError as e:

        error_body = e.read().decode("utf-8", errors="replace")

        st.error(f"HTTP 오류 코드: {e.code}")
        st.error(f"상세 오류 내용: {error_body}")

        return None

    except urllib.error.URLError as e:

        st.error(f"서버 연결 오류: {e.reason}")

        return None

    except Exception as e:

        st.error(f"기타 오류 발생: {e}")

        return None


# 9. Streamlit 화면 구성
st.title("디저트 유행 주기 분석 🍰")

# 사이드바 인증키 입력창
try:
    default_id = st.secrets.get("NAVER_CLIENT_ID", "")
    default_secret = st.secrets.get("NAVER_CLIENT_SECRET", "")
except Exception:
    default_id = ""
    default_secret = ""

st.sidebar.header("🔑 API 인증키 설정")
input_client_id = st.sidebar.text_input("NAVER Client ID", value=default_id, type="password")
input_client_secret = st.sidebar.text_input("NAVER Client Secret", value=default_secret, type="password")

df = get_ncp_trend_data(input_client_id.strip(), input_client_secret.strip())

if df is not None:

    # 1) 상단: 기존과 동일하게 전체 데이터 표 고정 출력
    st.subheader("수집된 실제 API 데이터 확인")
    st.dataframe(df, use_container_width=True)

    st.divider()

    # 2) 하단: 깔끔한 가로 체크박스 선택 + 그래프
    st.subheader("검색량 추이 그래프")

    desserts = df.columns.tolist()
    cols = st.columns(len(desserts))
    selected_desserts = []

    for col, dessert in zip(cols, desserts):
        with col:
            if st.checkbox(dessert, value=True, key=f"chk_{dessert}"):
                selected_desserts.append(dessert)

    if selected_desserts:
        st.line_chart(df[selected_desserts])
    else:
        st.info("그래프로 볼 디저트를 1개 이상 선택해주세요.")