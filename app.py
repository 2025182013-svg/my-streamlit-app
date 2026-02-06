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

openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
naver_client_id = st.sidebar.text_input("Naver Client ID", type="password")
naver_client_secret = st.sidebar.text_input("Naver Client Secret", type="password")

if not (openai_api_key and naver_client_id and naver_client_secret):
    st.warning("사이드바에 모든 API Key를 입력해주세요.")
    st.stop()

client = OpenAI(api_key=openai_api_key)

# =====================
# OpenAI Functions
# =====================
def generate_questions_and_keywords(topic, task_type):
    prompt = f"""
주제: {topic}
과제 유형: {task_type}

1. 위 주제에 대해 핵심 리서치 질문을 3개만 작성해줘.
2. 각 질문마다 네이버 뉴스 검색에 적합한 '키워드형 검색어'를 하나씩 만들어줘.
3. 마지막에 '최신 연구 동향'을 파악하기 위한 검색 키워드 1개를 추가해줘.

출력 형식:
[질문]
- 질문1
- 질문2
- 질문3

[검색키워드]
- 키워드1
- 키워드2
- 키워드3
- 최신 연구 동향 키워드
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    text = response.choices[0].message.content

    questions = []
    keywords = []
    section = None

    for line in text.split("\n"):
        line = line.strip()
        if "[질문]" in line:
            section = "q"
        elif "[검색키워드]" in line:
            section = "k"
        elif line.startswith("-"):
            if section == "q":
                questions.append(line[1:].strip())
            elif section == "k":
                keywords.append(line[1:].strip())

    return questions, keywords


def summarize_with_citation(text, source):
    prompt = f"""
아래 내용을 문서에 바로 인용할 수 있도록 2~3문장으로 요약해줘.
문장 끝에 반드시 출처를 포함해줘.

내용:
{text}

출처:
{source}
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return response.choices[0].message.content


# =====================
# Naver News API
# =====================
def search_naver_news(query, display=5):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret
    }
    params = {
        "query": query,
        "display": display,
        "sort": "date"
    }

    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        return res.json().get("items", [])
    except requests.exceptions.HTTPError:
        return []


# =====================
# Main UI
# =====================
st.title("📚 RefNote AI")
st.subheader("출처 기반 리서치 어시스턴트")

topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox("과제 유형", ["리포트", "기획서", "발표", "논문"])

if st.button("리서치 시작") and topic:
    with st.spinner("리서치 질문 및 검색어 생성 중..."):
        questions, keywords = generate_questions_and_keywords(topic, task_type)

    st.markdown("## 🔍 리서치 질문 (3개)")
    for q in questions:
        st.write("•", q)

    st.markdown("## 🧠 검색 키워드")
    for k in keywords:
        st.write("-", k)

    all_results = []

    with st.spinner("최신 자료 검색 중..."):
        for k in keywords:
            news_items = search_naver_news(k)

            for item in news_items:
                all_results.append({
                    "유형": "뉴스",
                    "제목": item["title"],
                    "요약": item["description"],
                    "출처": item["originallink"],
                    "연도": item["pubDate"][:4]
                })

    if not all_results:
        st.warning("검색 결과가 없습니다. 키워드를 줄이거나 바꿔보세요.")
        st.stop()

    df = pd.DataFrame(all_results)

    st.markdown("## 📊 근거 자료 테이블 (최신순)")
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
