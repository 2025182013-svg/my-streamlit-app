import streamlit as st
import requests
import pandas as pd
import re, html
from openai import OpenAI
from datetime import datetime
from urllib.parse import urlparse

# =====================
# Page Config
# =====================
st.set_page_config(page_title="RefNote AI", layout="wide")

# =====================
# Sidebar - API Keys
# =====================
st.sidebar.title("🔐 API Keys")
openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
naver_client_id = st.sidebar.text_input("Naver Client ID", type="password")
naver_client_secret = st.sidebar.text_input("Naver Client Secret", type="password")

if not (openai_api_key and naver_client_id and naver_client_secret):
    st.sidebar.warning("API Key를 모두 입력하세요.")
    st.stop()

client = OpenAI(api_key=openai_api_key)

# =====================
# Utils
# =====================
def clean_text(text):
    text = re.sub("<.*?>", "", text)
    return html.unescape(text)

def parse_date(pub_date):
    try:
        dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%d")
    except:
        return "N/A"

def apa_citation(row):
    domain = urlparse(row["출처"]).netloc.replace("www.", "")
    return f"{domain}. ({row['연도']}). {row['제목']}. {row['출처']}"

# =====================
# GPT Functions
# =====================
def generate_questions_and_keywords(topic, task_type):
    prompt = f"""
주제: {topic}
과제 유형: {task_type}

아래 JSON 형식으로만 답변해.

{{
  "questions": [
    "리서치 질문 1",
    "리서치 질문 2",
    "리서치 질문 3"
  ],
  "keywords": [
    "키워드1",
    "키워드2",
    "키워드3",
    "키워드4",
    "키워드5"
  ]
}}
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return eval(res.choices[0].message.content)

def summarize_trends(keywords):
    prompt = f"""
다음 키워드를 바탕으로 최신 연구 동향을 200자 이내로 요약해줘.
키워드: {", ".join(keywords)}
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return res.choices[0].message.content

# =====================
# News Search
# =====================
DEFAULT_BLOCK = ["연예", "가십", "스캔들"]

def search_naver_news(keywords, user_blocks):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret
    }

    rows = []

    for kw in keywords:
        params = {"query": kw, "display": 10, "sort": "date"}
        res = requests.get(url, headers=headers, params=params)
        if res.status_code != 200:
            continue

        for item in res.json().get("items", []):
            title = clean_text(item["title"])
            desc = clean_text(item["description"])

            # 사용자 제외 키워드 + 기본 블랙리스트
            if any(b in title for b in (DEFAULT_BLOCK + user_blocks)):
                continue

            # 키워드 최소 2개 이상 포함
            match = sum(k in title + desc for k in keywords)
            if match < 2:
                continue

            date = parse_date(item["pubDate"])

            rows.append({
                "제목": title,
                "요약": desc,
                "작성일": date,
                "연도": date[:4],
                "출처": item["originallink"],
                "관련도": match
            })

    df = pd.DataFrame(rows).drop_duplicates()
    return df

# =====================
# UI
# =====================
st.title("📚 RefNote AI")
st.caption("출처 기반 리서치 어시스턴트")

topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox("과제 유형", ["발표", "리포트", "기획서", "논문"])

exclude_input = st.text_input(
    "🚫 제외할 키워드 (선택)",
    placeholder="예: 인사, 웨딩, 사건"
)
user_blocks = [x.strip() for x in exclude_input.split(",") if x.strip()]

if st.button("리서치 시작") and topic:
    with st.spinner("리서치 진행 중..."):
        parsed = generate_questions_and_keywords(topic, task_type)
        news_df = search_naver_news(parsed["keywords"], user_blocks)
        trend = summarize_trends(parsed["keywords"])

        st.session_state.result = {
            "questions": parsed["questions"],
            "keywords": parsed["keywords"],
            "trend": trend,
            "news": news_df
        }

# =====================
# Output
# =====================
if "result" in st.session_state:
    r = st.session_state.result

    st.subheader("🔍 리서치 질문 (3개)")
    for q in r["questions"]:
        st.write("•", q)

    st.subheader("🔑 검색 키워드")
    st.write(", ".join(r["keywords"]))

    st.subheader("🧠 최신 연구 동향")
    st.write(r["trend"])

    st.subheader("📊 근거 자료")

    tab_news, tab_paper = st.tabs(["📰 뉴스", "📄 논문 (준비 중)"])

    with tab_news:
        sort_option = st.radio(
            "정렬 기준",
            ["관련도순", "최신순"],
            horizontal=True
        )

        df = r["news"]
        if not df.empty:
            if sort_option == "관련도순":
                df = df.sort_values("관련도", ascending=False)
            else:
                df = df.sort_values("작성일", ascending=False)

            st.dataframe(df[["제목", "작성일", "출처"]], use_container_width=True)

            st.subheader("📎 참고문헌 (APA 형식, TOP 10)")
            for i, row in enumerate(df.head(10).iterrows(), 1):
                st.write(f"{i}. {apa_citation(row[1])}")
        else:
            st.info("조건에 맞는 뉴스가 없습니다.")

    with tab_paper:
        st.info("DBpia 등 논문 API 연동 예정입니다.")
