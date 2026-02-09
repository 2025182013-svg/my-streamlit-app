import streamlit as st
import requests, html
from datetime import datetime
from openai import OpenAI
import pandas as pd
import io

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="RefNote AI", layout="wide")
st.title("📚 RefNote AI")
st.caption("핵심 키워드 기반 리서치 결과물 생성 도구 (APA 인용 · CSV 저장 지원)")

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
    return domain.replace("www.", "").split(".")[0].capitalize()

def apa_news(row):
    year = row["발행일"][:4] if row["발행일"] else "n.d."
    return f"{row['출처']}. ({year}). {row['제목']}. {row['링크']}"

# =====================
# AI 함수
# =====================
def gen_questions(topic):
    prompt = f"다음 주제에 대한 연구 질문 3개를 생성하세요:\n{topic}"
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return [q.strip("-• ").strip() for q in r.choices[0].message.content.split("\n") if q.strip()]

def gen_keywords(topic):
    prompt = f"다음 주제의 핵심 키워드 5개를 중요도순으로 쉼표로 출력:\n{topic}"
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return [k.strip() for k in r.choices[0].message.content.split(",")]

def gen_trend_summary(keywords):
    prompt = f"""
다음 키워드를 바탕으로 최신 연구 동향을 간단히 요약하세요.
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
# UI 입력
# =====================
topic = st.text_input("어떤 주제로 자료를 준비하나요?")

# =====================
# 리서치 실행
# =====================
if st.button("🔍 리서치 시작") and topic:
    with st.spinner("리서치 진행 중..."):
        questions = gen_questions(topic)
        keywords = gen_keywords(topic)

        news_raw = []
        for k in keywords[:2]:
            news_raw.extend(search_news(k))

        filtered = []
        for n in news_raw:
            s = relevance(topic, n)
            if s >= 2:
                n["score"] = s
                filtered.append(n)

        news_df = pd.DataFrame([
            {
                "제목": n["title"],
                "요약": n["desc"],
                "출처": format_source(n["link"].split("/")[2]),
                "발행일": n["date"].strftime("%Y-%m-%d") if n["date"] else "",
                "관련도": n["score"],
                "링크": n["link"]
            } for n in filtered
        ]).drop_duplicates(subset=["링크"])

        st.session_state.results = {
            "topic": topic,
            "questions": questions,
            "keywords": keywords,
            "trend": gen_trend_summary(keywords),
            "news": news_df
        }
        st.session_state.history.append(topic)

# =====================
# 결과 출력
# =====================
if st.session_state.results:
    r = st.session_state.results

    st.subheader("🔍 리서치 질문")
    for q in r["questions"]:
        st.markdown(f"• {q}")

    st.subheader("🔑 핵심 키워드")
    st.write(", ".join(r["keywords"]))

    st.subheader("📈 최신 연구 동향")
    st.markdown(r["trend"])

    sort = st.radio("정렬 기준", ["관련도순", "최신순"], horizontal=True)

    table = r["news"]
    if sort == "관련도순":
        table = table.sort_values(by="관련도", ascending=False)
    else:
        table = table.sort_values(by="발행일", ascending=False)

    st.subheader("📰 뉴스 기반 자료")
    st.dataframe(table, use_container_width=True)

    # =====================
    # CSV 다운로드 (Excel 호환)
    # =====================
    csv = table.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 리서치 결과 다운로드 (CSV / Excel 호환)",
        data=csv,
        file_name=f"{r['topic']}_research.csv",
        mime="text/csv"
    )

    st.subheader("📎 참고문헌 (APA 형식 · 정렬 반영)")
    for _, row in table.iterrows():
        st.markdown(f"- {apa_news(row)}")

# =====================
# 히스토리
# =====================
st.sidebar.header("📂 리서치 히스토리 (세션)")
for h in reversed(st.session_state.history):
    st.sidebar.write(f"• {h}")
