import streamlit as st
import requests
import pandas as pd
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
    st.sidebar.warning("API Key 입력 필요")
    st.stop()

client = OpenAI(api_key=openai_api_key)

# =====================
# Session State
# =====================
if "history" not in st.session_state:
    st.session_state.history = {}

if "current" not in st.session_state:
    st.session_state.current = None

# =====================
# OpenAI Functions
# =====================
def generate_questions_and_keywords(topic, task_type):
    prompt = f"""
주제: {topic}
과제 유형: {task_type}

아래 형식을 반드시 지켜.

[리서치 질문]
1. 질문 1
2. 질문 2
3. 질문 3

[검색 키워드] (중요도 순 5개)
- 키워드1
- 키워드2
- 키워드3
- 키워드4
- 키워드5
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        timeout=20
    )

    text = res.choices[0].message.content
    questions, keywords, section = [], [], None

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
다음 키워드를 기반으로 최신 연구 동향을 200자 이내로 요약해줘.
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
# Naver News API
# =====================
def search_naver_news(query, display=3):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": naver_client_id,
        "X-Naver-Client-Secret": naver_client_secret
    }
    params = {"query": query, "display": display, "sort": "date"}
    res = requests.get(url, headers=headers, params=params, timeout=10)
    if res.status_code == 200:
        return res.json().get("items", [])
    return []

# =====================
# APA Citation Generator
# =====================
def apa_citation(row):
    year = row["연도"]
    title = row["제목"]
    url = row["출처"]
    source = urlparse(url).netloc.replace("www.", "")

    return f"{source}. ({year}). {title}. {url}"

# =====================
# Sidebar - History
# =====================
st.sidebar.title("📂 저장된 리서치")

for task_type, topics in st.session_state.history.items():
    with st.sidebar.expander(task_type):
        for topic in topics:
            if st.button(topic, key=f"{task_type}-{topic}"):
                st.session_state.current = topics[topic]

# =====================
# Main UI
# =====================
st.title("📚 RefNote AI")
st.caption("출처 기반 리서치 어시스턴트")

topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox("과제 유형", ["발표", "리포트", "기획서", "논문"])

# =====================
# Research Start
# =====================
if st.button("리서치 시작") and topic:
    with st.spinner("리서치 진행 중..."):
        questions, keywords = generate_questions_and_keywords(topic, task_type)
        trend = summarize_latest_trends(keywords)

        rows = []
        for k in keywords:
            for item in search_naver_news(k):
                rows.append({
                    "제목": item["title"],
                    "요약": item["description"],
                    "출처": item["originallink"],
                    "연도": item["pubDate"][:4],
                    "관련도": keywords.index(k)
                })

        df = pd.DataFrame(rows).sort_values("관련도").head(10)

        result = {
            "topic": topic,
            "task_type": task_type,
            "questions": questions,
            "keywords": keywords,
            "trend": trend,
            "df": df
        }

        st.session_state.current = result
        st.session_state.history.setdefault(task_type, {})[topic] = result

# =====================
# Output
# =====================
if st.session_state.current:
    data = st.session_state.current

    st.subheader("🔍 리서치 질문 (3개)")
    for q in data["questions"]:
        st.write("-", q)

    st.subheader("🔑 사용된 검색 키워드 (중요도 순)")
    for i, k in enumerate(data["keywords"], 1):
        st.write(f"{i}. {k}")

    st.subheader("🧠 최신 연구 동향 요약")
    st.write(data["trend"])

    st.subheader("📊 근거 자료 테이블 (주요 관련도 순)")
    st.dataframe(data["df"][["제목", "연도", "출처"]], use_container_width=True)

    # =====================
    # APA Citations
    # =====================
    st.subheader("📎 참고문헌 (APA 형식, TOP 10)")

    for idx, row in data["df"].iterrows():
        citation = apa_citation(row)
        st.code(citation, language="text")
        st.button("📋 복사", key=f"copy-{idx}", on_click=lambda x=citation: st.session_state.update({"_clip": x}))
        st.divider()
