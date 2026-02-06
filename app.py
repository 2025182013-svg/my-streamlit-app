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
st.caption("출처 기반 리서치 어시스턴트 (뉴스 + 연구동향 / DBpia 확장 준비)")

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

if not openai_key or not naver_id or not naver_secret:
    st.warning("⬅️ 사이드바에 모든 API 키를 입력하세요.")
    st.stop()

client = OpenAI(api_key=openai_key)

# =====================
# 유틸
# =====================
def clean(t):
    return html.unescape(t).replace("<b>", "").replace("</b>", "").strip()

def parse_date(d):
    try:
        return datetime.strptime(d, "%a, %d %b %Y %H:%M:%S %z")
    except:
        return None

def format_source(domain):
    domain = domain.replace("www.", "")
    return domain.split(".")[0].capitalize()

# =====================
# AI 함수
# =====================
def gen_keywords(topic):
    prompt = f"다음 주제의 핵심 검색 키워드 5개를 중요도순으로 쉼표로 출력:\n{topic}"
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return [k.strip() for k in r.choices[0].message.content.split(",")]

def gen_trend_summary(keywords):
    prompt = f"""
    다음 키워드를 바탕으로 최근 연구 동향을 학술적으로 요약하세요.
    키워드: {', '.join(keywords)}
    """
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return r.choices[0].message.content.strip()

def relevance(topic, n):
    prompt = f"""
연구 주제: {topic}
뉴스 제목: {n['title']}
요약: {n['desc']}
관련도 0~3 숫자만 출력
"""
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    try:
        return int(r.choices[0].message.content.strip())
    except:
        return 0

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
# DBpia (미구현 – 구조만 유지)
# =====================
def search_dbpia(keyword):
    """
    TODO:
    - DBpia API 연동 예정
    - 반환 형식 예시:
      {
        "title": "",
        "authors": "",
        "journal": "",
        "year": "",
        "link": ""
      }
    """
    return []

# =====================
# UI 입력
# =====================
topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox("과제 유형", ["논문", "발표"])

# =====================
# 리서치 실행
# =====================
if st.button("🔍 리서치 시작") and topic:
    with st.spinner("리서치 진행 중..."):
        keywords = gen_keywords(topic)

        # 뉴스 수집
        news_raw = []
        for k in keywords[:2]:
            news_raw.extend(search_news(k))

        # 관련도 필터
        filtered_news = []
        for n in news_raw:
            s = relevance(topic, n)
            if s >= 2:
                n["score"] = s
                filtered_news.append(n)

        # 뉴스 DataFrame
        news_df = pd.DataFrame([
            {
                "유형": "뉴스",
                "제목": n["title"],
                "요약": n["desc"],
                "출처": format_source(n["link"].split("/")[2]),
                "연도": n["date"].year if n["date"] else "",
                "관련도": n["score"],
                "링크": n["link"]
            } for n in filtered_news
        ]).drop_duplicates(subset=["링크"])

        # 연구 동향 요약
        trend = gen_trend_summary(keywords)

        st.session_state.results = {
            "topic": topic,
            "keywords": keywords,
            "news": news_df,
            "trend": trend
        }
        st.session_state.history.append(topic)

# =====================
# 결과 출력
# =====================
if st.session_state.results:
    r = st.session_state.results

    st.subheader("🔑 핵심 키워드")
    st.write(", ".join(r["keywords"]))

    st.subheader("📈 최신 연구 동향 요약")
    st.markdown(r["trend"])

    st.subheader("📰 뉴스 기반 근거 자료")
    st.dataframe(r["news"], use_container_width=True)

    st.subheader("📎 참고문헌 (APA 7판 · 뉴스)")
    for _, row in r["news"].head(10).iterrows():
        st.markdown(
            f"- {row['출처']}. ({row['연도']}). {row['제목']}. {row['링크']}"
        )

# =====================
# 사이드바 - 히스토리
# =====================
st.sidebar.header("📂 리서치 히스토리")
for h in reversed(st.session_state.history):
    st.sidebar.write(f"• {h}")
