import streamlit as st
import requests
import pandas as pd
import re
from openai import OpenAI
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
# Session State
# =====================
if "result" not in st.session_state:
    st.session_state.result = None

# =====================
# Utils
# =====================
def clean_html(text):
    return re.sub("<.*?>", "", text)

# =====================
# GPT: Questions + Keywords (JSON)
# =====================
def generate_questions_and_keywords(topic, task_type):
    prompt = f"""
주제: {topic}
과제 유형: {task_type}

반드시 JSON 형식으로만 답변해.

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
        temperature=0.2,
        timeout=20
    )
    return eval(res.choices[0].message.content)

# =====================
# GPT: Research Trend
# =====================
def summarize_trends(keywords):
    prompt = f"""
다음 키워드를 바탕으로 교육·연구 관점의 최신 연구 동향을 200자 이내로 요약해줘.
키워드: {", ".join(keywords)}
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        timeout=15
    )
    return res.choices[0].message.content

# =====================
# Naver News Search (Filtered)
# =====================
def search_naver_news(keywords):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret
    }

    rows = []

    for kw in keywords:
        params = {"query": kw, "display": 10, "sort": "date"}
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code != 200:
            continue

        for item in res.json().get("items", []):
            title = clean_html(item["title"])
            desc = clean_html(item["description"])

            # 🔎 핵심 키워드 2개 이상 포함된 기사만
            match_count = sum(k in title + desc for k in keywords)
            if match_count < 2:
                continue

            rows.append({
                "제목": title,
                "요약": desc,
                "연도": item["pubDate"][:4],
                "출처": item["originallink"],
                "관련도": match_count
            })

    df = pd.DataFrame(rows)
    if df.empty:
        return df

    return df.sort_values(["관련도", "연도"], ascending=[False, False]).head(10)

# =====================
# APA Citation
# =====================
def apa(row):
    domain = urlparse(row["출처"]).netloc.replace("www.", "")
    return f"{domain}. ({row['연도']}). {row['제목']}. {row['출처']}"

# =====================
# UI
# =====================
st.title("📚 RefNote AI")
st.caption("출처 기반 리서치 어시스턴트")

topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox("과제 유형", ["발표", "리포트", "기획서", "논문"])

if st.button("리서치 시작") and topic:
    with st.spinner("리서치 진행 중..."):
        parsed = generate_questions_and_keywords(topic, task_type)
        questions = parsed["questions"]
        keywords = parsed["keywords"]

        trend = summarize_trends(keywords)
        df = search_naver_news(keywords)

        st.session_state.result = {
            "questions": questions,
            "keywords": keywords,
            "trend": trend,
            "df": df
        }

# =====================
# Output
# =====================
if st.session_state.result:
    r = st.session_state.result

    st.subheader("🔍 리서치 질문 (3개)")
    for q in r["questions"]:
        st.write("•", q)

    st.subheader("🔑 사용된 검색 키워드")
    st.write(", ".join(r["keywords"]))

    st.subheader("🧠 최신 연구 동향 요약")
    st.write(r["trend"])

    st.subheader("📊 근거 자료 테이블")
    st.dataframe(r["df"][["제목", "연도", "출처"]], use_container_width=True)

    st.subheader("📎 참고문헌 (APA 형식, TOP 10)")
    for i, row in enumerate(r["df"].iterrows(), 1):
        st.write(f"{i}. {apa(row[1])}")
