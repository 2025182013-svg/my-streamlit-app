import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from openai import OpenAI
import html

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="RefNote AI", layout="wide")

st.title("📚 RefNote AI")
st.caption("출처 기반 리서치 어시스턴트")

# -----------------------------
# Session State 초기화
# -----------------------------
if "history" not in st.session_state:
    st.session_state.history = []

if "current_result" not in st.session_state:
    st.session_state.current_result = None

# -----------------------------
# Sidebar - API Key 입력
# -----------------------------
st.sidebar.header("🔑 API 설정")

openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
naver_id = st.sidebar.text_input("Naver Client ID")
naver_secret = st.sidebar.text_input("Naver Client Secret")

client = None
if openai_key:
    client = OpenAI(api_key=openai_key)

# -----------------------------
# Sidebar - 저장된 리서치
# -----------------------------
st.sidebar.markdown("---")
st.sidebar.header("📂 저장된 리서치")

if st.session_state.history:
    for i, item in enumerate(reversed(st.session_state.history)):
        if st.sidebar.button(f"[{item['task']}] {item['topic']}", key=f"h_{i}"):
            st.session_state.current_result = item
else:
    st.sidebar.write("아직 저장된 리서치가 없습니다.")

# -----------------------------
# 입력 영역
# -----------------------------
topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox("과제 유형", ["논문", "리포트", "발표"])

# -----------------------------
# OpenAI - 리서치 질문 생성
# -----------------------------
def generate_questions(topic, task):
    prompt = f"""
주제: {topic}
과제 유형: {task}

이 주제에 대해 학술적으로 의미 있는 리서치 질문 3개만 생성해줘.
불필요한 설명 없이 질문만 출력해줘.
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return [q.strip("•- ") for q in res.choices[0].message.content.split("\n") if q.strip()]

# -----------------------------
# OpenAI - 키워드 & 연구 동향
# -----------------------------
def generate_keywords_and_trend(topic):
    prompt = f"""
주제: {topic}

1. 뉴스 및 학술 검색에 적합한 핵심 키워드 5개
2. 최근 연구 동향 요약 (3~4문장)

형식:
키워드: 키워드1, 키워드2, 키워드3, 키워드4, 키워드5
동향: 요약문
"""
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    text = res.choices[0].message.content
    keywords = text.split("키워드:")[1].split("동향:")[0].strip().split(",")
    trend = text.split("동향:")[1].strip()
    return [k.strip() for k in keywords], trend

# -----------------------------
# Naver 뉴스 검색
# -----------------------------
def search_news(query):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": naver_id,
        "X-Naver-Client-Secret": naver_secret,
    }
    params = {
        "query": query,
        "display": 30,
        "sort": "date",
    }

    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()

    items = []
    for item in res.json()["items"]:
        title = html.unescape(item["title"])
        desc = html.unescape(item["description"])

        pubdate = datetime.strptime(
            item["pubDate"], "%a, %d %b %Y %H:%M:%S %z"
        )

        items.append({
            "제목": title,
            "요약": desc,
            "출처": item["originallink"],
            "작성일": pubdate.strftime("%Y-%m-%d"),
        })

    return pd.DataFrame(items)

# -----------------------------
# APA 참고문헌 생성
# -----------------------------
def make_apa(df):
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
if st.button("🔍 리서치 시작") and client:
    with st.spinner("리서치 진행 중..."):
        questions = generate_questions(topic, task_type)
        keywords, trend = generate_keywords_and_trend(topic)
        news_df = search_news(" ".join(keywords))
        references = make_apa(news_df)

        result = {
            "topic": topic,
            "task": task_type,
            "questions": questions,
            "keywords": keywords,
            "trend": trend,
            "news": news_df,
            "refs": references,
        }

        st.session_state.history.append(result)
        st.session_state.current_result = result

# -----------------------------
# 결과 출력
# -----------------------------
data = st.session_state.current_result

if data:
    st.markdown("## 🔍 리서치 질문 (3개)")
    for q in data["questions"]:
        st.write(f"• {q}")

    st.markdown("## 🔑 검색 키워드")
    st.write(", ".join(data["keywords"]))

    st.markdown("## 🧠 최신 연구 동향")
    st.write(data["trend"])

    st.markdown("## 📊 근거 자료 (뉴스, 최신순)")
    st.dataframe(data["news"], use_container_width=True)

    st.markdown("## 📎 참고문헌 (APA 형식, TOP 10)")
    for r in data["refs"]:
        st.write(r)
