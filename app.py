import streamlit as st
import requests, html
from datetime import datetime
from openai import OpenAI
import pandas as pd

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="RefNote AI", layout="wide")
st.title("📚 RefNote AI")
st.caption("리서치 어시스턴트 (뉴스 + 학술 + 최신 연구 동향)")

# =====================
# 세션 상태
# =====================
if "results" not in st.session_state:
    st.session_state.results = None
if "history" not in st.session_state:
    st.session_state.history = []

# =====================
# 사이드바 - API
# =====================
st.sidebar.header("🔑 API 설정")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
naver_id = st.sidebar.text_input("Naver Client ID", type="password")
naver_secret = st.sidebar.text_input("Naver Client Secret", type="password")
dbpia_key = st.sidebar.text_input("DBpia API Key", type="password")

if not openai_key or not naver_id or not naver_secret:
    st.warning("⬅️ API 키들을 모두 입력하세요.")
    st.stop()

client = OpenAI(api_key=openai_key)

# =====================
# 유틸
# =====================
def clean(t): return html.unescape(t).replace("<b>", "").replace("</b>", "").strip()
def parse_date(d):
    try:
        return datetime.strptime(d, "%a, %d %b %Y %H:%M:%S %z")
    except:
        return None

def format_source(domain):
    domain = domain.replace("www.", "")
    base = domain.split(".")[0]
    return base.capitalize()

# =====================
# AI 서머리
# =====================
def gen_trend_summary(keywords):
    prompt = f"""
    다음 키워드에 대한 최신 연구 동향을 요약하시오:
    {', '.join(keywords)}
    """
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.2
    )
    return r.choices[0].message.content.strip()

# =====================
# 네이버 뉴스
# =====================
def search_news(q):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": naver_id,
        "X-Naver-Client-Secret": naver_secret
    }
    params = {"query": q, "display": 30, "sort": "date"}
    r = requests.get(url, headers=headers, params=params).json()
    out = []
    for i in r.get("items", []):
        out.append({
            "title": clean(i["title"]),
            "desc": clean(i["description"]),
            "link": i["link"],
            "date": parse_date(i["pubDate"])
        })
    return out

# =====================
# DBpia 검색 함수 (나중에 채워)
# =====================
def search_dbpia(q):
    # TODO: DBpia API 연결
    # 예) requests.get("DBpiaURL?apikey=...")
    return []

# =====================
# 리서치 실행
# =====================
topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox("과제 유형", ["논문", "발표"])
if st.button("🔍 리서치 시작") and topic:

    with st.spinner("리서치 진행 중..."):
        # 키워드 생성
        kws = gen_keywords(topic)

        # 뉴스
        news_raw = []
        for k in kws[:2]:
            news_raw.extend(search_news(k))

        # 학술
        dbpia_raw = []
        if dbpia_key:
            for k in kws[:3]:
                dbpia_raw.extend(search_dbpia(k))

        # 관련도 평가 (뉴스만)
        filtered_news = []
        for n in news_raw:
            s = relevance(topic, n)
            if s >= 2:
                n["score"] = s
                filtered_news.append(n)

        # 뉴스 DataFrame
        news_df = pd.DataFrame([
            {
                "제목": n["title"],
                "요약": n["desc"],
                "도메인": n["link"].split("/")[2],
                "출처": format_source(n["link"].split("/")[2]),
                "연도": n["date"].year if n["date"] else "",
                "관련도": n["score"],
                "링크": n["link"]
            } for n in filtered_news
        ]).drop_duplicates(subset=["링크"])

        # 학술 DataFrame (아직 구조 예시)
        dbpia_df = pd.DataFrame(dbpia_raw)

        # 최신동향 요약
        trend_summary = gen_trend_summary(kws)

        # 결과 저장
        st.session_state.results = {
            "topic": topic,
            "keywords": kws,
            "news": news_df,
            "dbpia": dbpia_df,
            "trend": trend_summary
        }
        st.session_state.history.append(topic)

# =====================
# 결과 출력
# =====================
if st.session_state.results:
    r = st.session_state.results

    st.subheader("🔍 키워드")
    st.write(", ".join(r["keywords"]))

    st.subheader("📌 최신 연구 동향 요약")
    st.markdown(r["trend"])

    # 뉴스 섹션
    st.subheader("📰 뉴스 기반 자료")
    st.dataframe(r["news"])

    # 학술 섹션
    st.subheader("📄 학술 자료 (DBpia)")
    st.dataframe(r["dbpia"])

    # APA 참고문헌
    st.subheader("📎 참고문헌 (APA 7판)")
    if not r["news"].empty:
        st.markdown("**뉴스**")
        for _, row in r["news"].iterrows():
            st.markdown(
                f"- {row['출처']}. ({row['연도']}). {row['제목']}. {row['링크']}"
            )
    if not r["dbpia"].empty:
        st.markdown("**학술논문**")
        for _, row in r["dbpia"].iterrows():
            st.markdown(
                f"- {row['authors']} ({row['year']}). {row['title']}. {row['journal']}. {row['link']}"
            )

# =====================
# 사이드바 - 히스토리
# =====================
st.sidebar.header("📂 리서치 히스토리")
for h in reversed(st.session_state.history):
    st.sidebar.write(f"• {h}")
