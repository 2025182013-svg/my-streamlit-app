import streamlit as st
import requests, html, json, os
from datetime import datetime
from openai import OpenAI
import pandas as pd
import io

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="RefNote AI", layout="wide")
st.title("📚 RefNote AI")
st.caption("핵심 키워드 기반 리서치 결과물 생성 도구 (APA 7판 · CSV 다운로드 · 검색 내역 저장)")

# =====================
# 세션 상태 초기화
# =====================
if "results" not in st.session_state:
    st.session_state.results = None
if "history" not in st.session_state:
    st.session_state.history = []

HISTORY_FILE = "history.json"

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

# APA 7판 웹 뉴스 형식
def apa_news(row):
    author = row.get("저자", row["출처"])
    year = row["발행일"][:4] if row["발행일"] else "n.d."
    return f"{author}. ({year}). {row['제목']}. {row['출처']}. {row['링크']}"

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
# 뉴스 검색
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
            "제목": clean(i["title"]),
            "요약": clean(i["description"]),
            "출처": format_source(i["link"].split("/")[2]),
            "발행일": parse_date(i["pubDate"]).strftime("%Y-%m-%d") if parse_date(i["pubDate"]) else "",
            "링크": i["link"]
        })
    return out

# =====================
# 논문(DBpia) 미구현
# =====================
def search_dbpia(keyword):
    return pd.DataFrame(columns=["제목","저자","학술지","연도","링크"])

# =====================
# 리서치 실행
# =====================
topic = st.text_input("어떤 주제로 자료를 준비하나요?")

if st.button("🔍 리서치 시작") and topic:
    with st.spinner("리서치 진행 중..."):
        questions = gen_questions(topic)
        keywords = gen_keywords(topic)

        # 뉴스 검색
        news_list = []
        for k in keywords[:2]:
            news_list.extend(search_news(k))

        # 관련도 필터링
        filtered = []
        for n in news_list:
            n["score"] = relevance(topic, n)
            if n["score"] >= 2:
                filtered.append(n)

        news_df = pd.DataFrame(filtered).drop_duplicates(subset=["링크"])
        paper_df = search_dbpia(topic)  # 미구현

        trend_summary = gen_trend_summary(keywords)

        # 세션에 저장
        st.session_state.results = {
            "topic": topic,
            "questions": questions,
            "keywords": keywords,
            "trend": trend_summary,
            "news": news_df,
            "papers": paper_df
        }

        # 검색 내역 JSON 저장
        st.session_state.history.append(topic)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.history, f, ensure_ascii=False, indent=2)

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

    # 뉴스 / 논문 탭
    tab_news, tab_paper = st.tabs(["📰 뉴스", "📄 논문 (DBpia 예정)"])

    # ---------------------
    # 뉴스 탭
    # ---------------------
    with tab_news:
        sort = st.radio("정렬 기준", ["관련도순", "최신순"], horizontal=True)
        news_table = r["news"]
        if sort == "관련도순":
            news_table = news_table.sort_values(by="score", ascending=False)
        else:
            news_table = news_table.sort_values(by="발행일", ascending=False)

        st.dataframe(news_table, use_container_width=True)

        # CSV 다운로드
        csv_news = news_table.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 뉴스 리서치 CSV 다운로드",
            data=csv_news,
            file_name=f"{r['topic']}_news.csv",
            mime="text/csv"
        )

        # APA 상위 10개
        st.subheader("📎 뉴스 참고문헌 (APA 7판 · 상위 10개)")
        for _, row in news_table.head(10).iterrows():
            st.markdown(f"- {apa_news(row)}")

    # ---------------------
    # 논문 탭
    # ---------------------
    with tab_paper:
        st.info("DBpia 연동 예정 영역입니다.")
        st.dataframe(r["papers"], use_container_width=True)

        # CSV 다운로드 (빈 데이터프레임)
        csv_paper = r["papers"].to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 논문 CSV 다운로드",
            data=csv_paper,
            file_name=f"{r['topic']}_papers.csv",
            mime="text/csv"
        )

# =====================
# 사이드바 - 검색 내역 복원
# =====================
st.sidebar.header("📂 리서치 히스토리")
# 저장된 JSON 파일 읽기
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        saved_history = json.load(f)
else:
    saved_history = []

for h in reversed(saved_history):
    if st.sidebar.button(h):
        st.session_state.results = st.session_state.results or {}
        st.session_state.results["topic"] = h
        st.info(f"'{h}' 주제 선택됨. 리서치 재실행 가능.")
