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
    st.warning("API Key를 모두 입력해주세요.")
    st.stop()

client = OpenAI(api_key=openai_api_key)

# =====================
# Session State Init
# =====================
state_defaults = {
    "questions": None,
    "keywords": None,
    "trend": None,
    "df": None,
    "summaries": None,
    "shown": 5
}
for k, v in state_defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================
# OpenAI Functions
# =====================
def generate_questions_and_keywords(topic, task_type):
    prompt = f"""
주제: {topic}
과제 유형: {task_type}

아래 형식을 반드시 지켜서 출력해줘.

[리서치 질문]
1. 질문 1
2. 질문 2
3. 질문 3

[검색 키워드] (중요도 순, 5개)
- 키워드1
- 키워드2
- 키워드3
- 키워드4
- 키워드5
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    text = res.choices[0].message.content

    questions, keywords = [], []
    section = None

    for line in text.split("\n"):
        line = line.strip()

        if "[리서치 질문]" in line:
            section = "q"
        elif "[검색 키워드]" in line:
            section = "k"
        elif section == "q" and line[:2].isdigit():
            questions.append(line.split(".", 1)[1].strip())
        elif section == "k" and line.startswith("-"):
            keywords.append(line[1:].strip())

    return questions, keywords


def summarize_latest_trends(keywords):
    prompt = f"""
다음 키워드를 기반으로 최신 연구 동향을 200~300자 이내로 요약해줘.
키워드: {", ".join(keywords)}
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return res.choices[0].message.content


def summarize_with_citation(text, source):
    prompt = f"""
아래 내용을 문서에 바로 인용 가능한 문장으로 2~3문장 요약해줘.
반드시 출처를 포함해줘.

내용:
{text}

출처:
{source}
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )
    return res.choices[0].message.content


# =====================
# Naver News API
# =====================
def search_naver_news(query, display=5):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret
    }
    params = {"query": query, "display": display, "sort": "date"}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        return res.json().get("items", [])
    return []

# =====================
# UI
# =====================
st.title("📚 RefNote AI")
st.caption("출처 기반 리서치 어시스턴트")

topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox("과제 유형", ["리포트", "기획서", "발표", "논문"])

# =====================
# Research Start
# =====================
if st.button("리서치 시작") and topic:
    with st.spinner("리서치 진행 중..."):
        qs, ks = generate_questions_and_keywords(topic, task_type)
        trend = summarize_latest_trends(ks)

        rows = []
        for k in ks:
            for item in search_naver_news(k):
                rows.append({
                    "제목": item["title"],
                    "요약": item["description"],
                    "출처": item["originallink"],
                    "연도": item["pubDate"][:4]
                })

        df = pd.DataFrame(rows)

        summaries = [
            summarize_with_citation(
                r["요약"], f"{r['출처']} ({r['연도']})"
            )
            for _, r in df.iterrows()
        ]

        st.session_state.questions = qs
        st.session_state.keywords = ks
        st.session_state.trend = trend
        st.session_state.df = df
        st.session_state.summaries = summaries
        st.session_state.shown = 5

# =====================
# Output
# =====================
if st.session_state.questions:
    st.subheader("🔍 리서치 질문 (3개)")
    for q in st.session_state.questions:
        st.write("-", q)

    st.subheader("🔑 사용된 검색 키워드 (중요도 순)")
    for i, k in enumerate(st.session_state.keywords, 1):
        st.write(f"{i}. {k}")

    st.subheader("🧠 최신 연구 동향 요약")
    st.write(st.session_state.trend)

    st.subheader("📊 근거 자료 테이블 (최신순)")
    st.dataframe(st.session_state.df, use_container_width=True)

    st.subheader("✍️ 인용 가능한 요약 문장")

    max_show = min(st.session_state.shown, len(st.session_state.summaries))
    for i in range(max_show):
        st.code(st.session_state.summaries[i], language="text")
        st.divider()

    if st.session_state.shown < len(st.session_state.summaries):
        if st.button("🔽 더보기"):
            st.session_state.shown += 5
