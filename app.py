import streamlit as st
import pandas as pd
import requests
import re
from openai import OpenAI

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title="출처 기반 리서치 어시스턴트",
    layout="wide"
)

st.title("📚 출처 기반 리서치 어시스턴트")

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
# 사이드바
# -----------------------------
with st.sidebar:
    st.header("🔐 API 설정")
    api_key = st.text_input(
        "OpenAI API Key",
        type="password",
        help="입력한 키는 저장되지 않습니다"
    )

    if api_key:
        client = OpenAI(api_key=api_key)

    st.divider()
    st.header("🗂 리서치 기록")

    if st.session_state.history:
        for k in st.session_state.history:
            if st.button(k):
                st.session_state.current_result = st.session_state.history[k]

# -----------------------------
# 입력 영역
# -----------------------------
topic = st.text_input(
    "어떤 주제로 자료를 준비하나요?",
    placeholder="예: 유아교육 공공성 인식과 출산 태도의 관계"
)

task_type = st.selectbox(
    "과제 유형",
    ["논문", "발표"]
)

# -----------------------------
# 유틸 함수
# -----------------------------
def clean_text(text):
    text = re.sub(r"<.*?>", "", text)
    text = text.replace("&quot;", "\"")
    return text.strip()

def fetch_news(query):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "ko",
        "pageSize": 30,
        "sortBy": "publishedAt",
        "apiKey": "demo"  # 실제 사용 시 교체
    }
    res = requests.get(url, params=params)
    if res.status_code != 200:
        return []
    return res.json().get("articles", [])

def judge_relevance(client, topic, title):
    prompt = f"""
주제: {topic}
뉴스 제목: {title}

이 뉴스가 연구 주제와 실질적으로 관련이 있으면 1,
관련 없으면 0으로만 답하세요.
"""
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    return int(r.choices[0].message.content.strip())

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
if st.button("🔍 리서치 시작") and api_key and topic:
    with st.spinner("리서치 진행 중..."):
        # 리서치 질문
        q_prompt = f"{topic}에 대한 학술적 리서치 질문 3개를 불릿으로 생성해줘."
        questions = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": q_prompt}]
        ).choices[0].message.content

        # 키워드
        k_prompt = f"{topic}에 대한 핵심 검색 키워드 5개를 중요도순으로 제시해줘."
        keywords = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": k_prompt}]
        ).choices[0].message.content

        # 연구 동향
        t_prompt = f"{topic}에 대한 최근 연구 동향을 4~5문장으로 요약해줘."
        trend = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": t_prompt}]
        ).choices[0].message.content

        # 뉴스 수집
        articles = fetch_news(topic)
        rows = []

        for a in articles:
            title = clean_text(a["title"])
            if judge_relevance(client, topic, title) == 0:
                continue

            rows.append({
                "제목": title,
                "출처": a["url"],
                "작성일": a["publishedAt"][:10],
                "관련도": len(set(topic.split()) & set(title.split()))
            })

        news_df = pd.DataFrame(rows)

        result = {
            "topic": topic,
            "task": task_type,
            "questions": questions,
            "keywords": keywords,
            "trend": trend,
            "news": news_df,
            "papers": pd.DataFrame()  # 논문 연동 예정
        }

        st.session_state.current_result = result
        st.session_state.history[f"{task_type} | {topic}"] = result

# -----------------------------
# 결과 출력
# -----------------------------
if st.session_state.current_result:
    data = st.session_state.current_result

    st.subheader("🔍 리서치 질문 (3개)")
    st.markdown(data["questions"])

    st.subheader("🔑 검색 키워드")
    st.markdown(data["keywords"])

    st.subheader("🧠 최신 연구 동향")
    st.markdown(data["trend"])

    st.subheader("📊 근거 자료")

    tab_news, tab_paper = st.tabs(["📰 뉴스", "📄 논문"])

    # ---------------- 뉴스 탭 ----------------
    with tab_news:
        st.radio(
            "정렬 기준 (뉴스)",
            ["관련도순", "최신순"],
            key="news_sort",
            horizontal=True
        )

        df = data["news"]

        if not df.empty:
            if st.session_state.news_sort == "관련도순":
                sorted_df = df.sort_values("관련도", ascending=False)
            else:
                sorted_df = df.sort_values("작성일", ascending=False)

            st.dataframe(
                sorted_df.drop(columns=["관련도"]),
                use_container_width=True
            )

            st.subheader("📎 참고문헌 (APA 형식, TOP 10)")
            for r in make_apa(sorted_df):
                st.write(r)
        else:
            st.info("관련성 높은 뉴스 자료를 찾지 못했습니다.")

    # ---------------- 논문 탭 ----------------
    with tab_paper:
        st.radio(
            "정렬 기준 (논문)",
            ["관련도순", "최신순"],
            key="paper_sort",
            horizontal=True
        )

        st.info("📄 논문 데이터는 현재 연동 예정입니다.")
