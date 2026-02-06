import streamlit as st
import requests
import pandas as pd
from openai import OpenAI

# =====================
# Page Config
# =====================
st.set_page_config(page_title="RefNote AI", layout="wide")

# =====================
# Sidebar - API Keys
# =====================
st.sidebar.title("🔐 API Keys")

openai_api_key = st.sidebar.text_input(
    "OpenAI API Key", type="password"
)
naver_client_id = st.sidebar.text_input(
    "Naver Client ID", type="password"
)
naver_client_secret = st.sidebar.text_input(
    "Naver Client Secret", type="password"
)

# Guard clause
if not (openai_api_key and naver_client_id and naver_client_secret):
    st.warning("사이드바에 모든 API Key를 입력해주세요.")
    st.stop()

# OpenAI client (NEW SDK)
client = OpenAI(api_key=openai_api_key)

# =====================
# OpenAI Functions
# =====================
def generate_research_questions(topic, task_type):
    prompt = f"""
주제: {topic}
과제 유형: {task_type}

위 주제에 대해 신뢰 가능한 자료 조사를 하기 위한
핵심 리서치 질문을 3~5개 생성해줘.
각 질문은 검색 키워드로 바로 사용할 수 있게 작성해줘.
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return [
        q.strip("-• ").strip()
        for q in response.choices[0].message.content.split("\n")
        if q.strip()
    ]


def summarize_with_citation(text, source):
    prompt = f"""
아래 내용을 문서에 바로 인용할 수 있도록
2~3문장으로 요약해줘.
문장 끝에 반드시 출처를 포함해줘.

내용:
{text}

출처:
{source}
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    return response.choices[0].message.content


# =====================
# Naver News API
# =====================
def search_naver_news(query, display=5, sort="date"):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret
    }
    params = {
        "query": query,
        "display": display,
        "sort": sort
    }

    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()

    return res.json().get("items", [])


# =====================
# Main UI
# =====================
st.title("📚 RefNote AI")
st.subheader("출처 기반 리서치 어시스턴트")

topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox(
    "과제 유형",
    ["리포트", "기획서", "발표", "논문"]
)

if st.button("리서치 시작") and topic:
    with st.spinner("리서치 질문 생성 중..."):
        questions = generate_research_questions(topic, task_type)

    st.markdown("## 🔍 리서치 질문")
    for q in questions:
        st.write("•", q)

    all_results = []

    with st.spinner("자료 검색 중..."):
        for q in questions[:3]:
            news_items = search_naver_news(q)

            for item in news_items:
                all_results.append({
                    "유형": "뉴스",
                    "제목": item["title"],
                    "요약": item["description"],
                    "출처": item["originallink"],
                    "연도": item["pubDate"][:4]
                })

    if not all_results:
        st.warning("검색 결과가 없습니다.")
        st.stop()

    df = pd.DataFrame(all_results)

    st.markdown("## 📊 근거 자료 테이블")
    st.dataframe(df, use_container_width=True)

    st.markdown("## ✍️ 인용 가능한 요약 문장")
    for _, row in df.iterrows():
        summary = summarize_with_citation(
            row["요약"],
            f"{row['출처']} ({row['연도']})"
        )
        st.markdown(f"**{row['제목']}**")
        st.write(summary)
        st.divider()
