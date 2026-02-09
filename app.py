import streamlit as st
import requests
import pandas as pd
import html
from datetime import datetime
from openai import OpenAI
import re

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="RefNote AI", layout="wide")
st.title("📚 RefNote AI")
st.caption("출처 기반 리서치 어시스턴트")

# -----------------------------
# 세션 상태 초기화
# -----------------------------
if "history" not in st.session_state:
    st.session_state.history = {}

if "current_result" not in st.session_state:
    st.session_state.current_result = None

if "news_sort" not in st.session_state:
    st.session_state.news_sort = "관련도순"

if "paper_sort" not in st.session_state:
    st.session_state.paper_sort = "관련도순"

# -----------------------------
# 사이드바 - API Keys
# -----------------------------
st.sidebar.header("🔑 API 설정")

openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
naver_client_id = st.sidebar.text_input("Naver Client ID", type="password")
naver_client_secret = st.sidebar.text_input("Naver Client Secret", type="password")

if openai_key:
    client = OpenAI(api_key=openai_key)
else:
    client = None

st.sidebar.markdown("---")
st.sidebar.header("📂 리서치 기록")

if st.session_state.history:
    for label in st.session_state.history:
        if st.sidebar.button(label):
            st.session_state.current_result = st.session_state.history[label]
else:
    st.sidebar.write("아직 저장된 리서치가 없습니다.")

# -----------------------------
# 입력 영역
# -----------------------------
topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox("과제 유형", ["논문", "발표"])

# -----------------------------
# 유틸 함수
# -----------------------------
def clean_text(text):
    text = re.sub(r"<.*?>", "", text)
    text = html.unescape(text)
    return text.strip()

def parse_date(pub_date):
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%d")
    except:
        return pub_date

# -----------------------------
# 리서치 질문 생성
# -----------------------------
def generate_questions(topic, task_type):
    prompt = f"""
주제: {topic}
과제 유형: {task_type}

아래 형식으로 리서치 질문 3개를 출력하세요 (한 줄씩)
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    lines = res.choices[0].message.content.split("\n")
    return [l.strip("•- ").strip() for l in lines if l.strip()]

# -----------------------------
# 키워드 & 최신 연구 동향
# -----------------------------
def generate_keywords_trend(topic):
    prompt = f"""
주제: {topic}

1. 검색용 핵심 키워드 5개를 쉼표로 출력
2. 최신 연구 동향을 3~5문장 요약

형식:
키워드: a, b, c, d, e
동향: ~
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    text = res.choices[0].message.content
    parts = text.split("동향:")
    keys_part = parts[0].split("키워드:")[-1].strip()
    keywords = [k.strip() for k in keys_part.split(",")]
    trend = parts[1].strip() if len(parts) > 1 else ""
    return keywords, trend

# -----------------------------
# 네이버 뉴스 API 검색
# -----------------------------
def search_naver_news(keywords):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret
    }
    all_items = []

    for kw in keywords:
        params = {
            "query": kw,
            "display": 30,
            "sort": "date"
        }
        try:
            res = requests.get(url, headers=headers, params=params, timeout=10)
            res.raise_for_status()
        except:
            continue

        items = res.json().get("items", [])
        for item in items:
            title = clean_text(item["title"])
            desc = clean_text(item["description"])
            pubdate = parse_date(item["pubDate"])
            link = item["originallink"]

            all_items.append({
                "제목": title,
                "요약": desc,
                "출처": link,
                "작성일": pubdate
            })

    df = pd.DataFrame(all_items).drop_duplicates()
    return df

# -----------------------------
# 관련도 계산 (키워드 출현 빈도)
# -----------------------------
def calculate_relevance(df, keywords):
    df["관련도"] = df["제목"].apply(lambda t: sum(t.count(k) for k in keywords))
    return df

# -----------------------------
# APA 참고문헌 생성
# -----------------------------
def make_apa_list(df):
    refs = []
    for _, r in df.head(10).iterrows():
        domain = r["출처"].split("/")[2]
        refs.append(
            f"{domain}. ({r['작성일']}). {r['제목']}. {r['출처']}"
        )
    return refs

# -----------------------------
# 리서치 실행
# -----------------------------
if st.button("🔍 리서치 시작") and client and naver_client_id and naver_client_secret and topic:
    with st.spinner("리서치 진행 중..."):
        # 리서치 질문
        questions = generate_questions(topic, task_type)

        # 키워드 + 최신 연구 동향
        keywords, trend = generate_keywords_trend(topic)

        # 뉴스 수집
        news_df = search_naver_news(keywords)
        news_df = calculate_relevance(news_df, keywords)

        result = {
            "topic": topic,
            "task": task_type,
            "questions": questions,
            "keywords": keywords,
            "trend": trend,
            "news": news_df,
            "papers": pd.DataFrame()  # 추후 논문 연동 예정
        }
        label = f"[{task_type}] {topic}"
        st.session_state.history[label] = result
        st.session_state.current_result = result

# -----------------------------
# 결과 출력
# -----------------------------
data = st.session_state.current_result

if data:
    st.subheader("🔍 리서치 질문 (3개)")
    for q in data["questions"]:
        st.write("•", q)

    st.subheader("🔑 검색 키워드")
    st.write(", ".join(data["keywords"]))

    st.subheader("🧠 최신 연구 동향")
    st.write(data["trend"])

    tab1, tab2 = st.tabs(["📰 뉴스", "📄 논문"])

    # ---------------- 뉴스 탭 ----------------
    with tab1:
        st.radio(
            "뉴스 정렬 기준",
            ["관련도순", "최신순"],
            key="news_sort",
            horizontal=True
        )

        df = data["news"]
        if not df.empty:
            if st.session_state.news_sort == "관련도순":
                sorted_news = df.sort_values("관련도", ascending=False)
            else:
                sorted_news = df.sort_values("작성일", ascending=False)

            st.dataframe(
                sorted_news.drop(columns=["관련도"]),
                use_container_width=True
            )

            st.subheader("📎 참고문헌 (APA 형식, TOP 10)")
            for ref in make_apa_list(sorted_news):
                st.write(ref)
        else:
            st.info("관련 뉴스가 없습니다.")

    # ---------------- 논문 탭 ----------------
    with tab2:
        st.radio(
            "논문 정렬 기준",
            ["관련도순", "최신순"],
            key="paper_sort",
            horizontal=True
        )
        st.info("📄 논문 API 연동 예정입니다.")
