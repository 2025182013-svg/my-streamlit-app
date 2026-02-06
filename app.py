import streamlit as st
import requests
import html
from datetime import datetime
from openai import OpenAI

# =========================
# 기본 설정
# =========================
st.set_page_config(page_title="RefNote AI", layout="wide")
st.title("📚 RefNote AI")
st.caption("출처 기반 리서치 어시스턴트")

# =========================
# API 설정
# =========================
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

NAVER_CLIENT_ID = st.secrets["NAVER_CLIENT_ID"]
NAVER_CLIENT_SECRET = st.secrets["NAVER_CLIENT_SECRET"]

# =========================
# 유틸 함수
# =========================
def clean_text(text):
    return html.unescape(text).replace("<b>", "").replace("</b>", "").strip()

def parse_date(date_str):
    try:
        return datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S %z")
    except:
        return None

# =========================
# 1. 리서치 질문 생성
# =========================
def generate_research_questions(topic):
    prompt = f"""
    다음 연구 주제에 대해 학술적으로 적절한 연구 질문 3개를 생성해줘.
    번호 없이 불릿(-) 형태로 출력.

    주제: {topic}
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return [
        q.strip("- ").strip()
        for q in res.choices[0].message.content.split("\n")
        if q.strip()
    ]

# =========================
# 2. 검색 키워드 추출
# =========================
def extract_keywords(topic):
    prompt = f"""
    다음 연구 주제에서 검색용 핵심 키워드 5개를 중요도 순으로 추출해줘.
    쉼표(,)로만 구분해서 출력.

    주제: {topic}
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return [k.strip() for k in res.choices[0].message.content.split(",")]

# =========================
# 3. 네이버 뉴스 검색
# =========================
def search_naver_news(query):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": NAVER_CLIENT_SECRET
    }
    params = {
        "query": query,
        "display": 30,
        "sort": "date"
    }

    res = requests.get(url, headers=headers, params=params)
    res.raise_for_status()

    results = []
    for item in res.json()["items"]:
        results.append({
            "title": clean_text(item["title"]),
            "description": clean_text(item["description"]),
            "link": item["link"],
            "date": parse_date(item["pubDate"])
        })
    return results

# =========================
# 4. AI 뉴스 관련도 평가
# =========================
def relevance_score(topic, news):
    prompt = f"""
    다음 뉴스가 연구 주제와 얼마나 관련 있는지 0~3점으로 평가해줘.
    숫자만 출력.

    연구 주제: {topic}
    뉴스 제목: {news['title']}
    뉴스 요약: {news['description']}
    """

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    try:
        return int(res.choices[0].message.content.strip())
    except:
        return 0

# =========================
# 5. APA 참고문헌 변환
# =========================
def to_apa(news):
    year = news["date"].year if news["date"] else "n.d."
    domain = news["link"].split("/")[2]
    return f"{domain}. ({year}). {news['title']}. {news['link']}"

# =========================
# UI 입력
# =========================
topic = st.text_input("어떤 주제로 자료를 준비하나요?")
task_type = st.selectbox("과제 유형", ["논문", "발표"])

if st.button("🔍 리서치 시작") and topic:
    with st.spinner("리서치 진행 중..."):

        # 리서치 질문
        questions = generate_research_questions(topic)
        st.subheader("🔍 리서치 질문 (3개)")
        for q in questions:
            st.markdown(f"• {q}")

        # 키워드
        keywords = extract_keywords(topic)
        st.subheader("🔑 검색 키워드")
        st.write(", ".join(keywords))

        # 뉴스 수집
        all_news = []
        for kw in keywords[:2]:
            all_news.extend(search_naver_news(kw))

        # AI 필터링
        filtered = []
        for n in all_news:
            score = relevance_score(topic, n)
            if score >= 2:
                n["score"] = score
                filtered.append(n)

        # 정렬
        sort_option = st.radio("정렬 기준", ["관련도순", "최신순"], horizontal=True)

        if sort_option == "관련도순":
            filtered.sort(key=lambda x: (-x["score"], x["date"] or datetime.min))
        else:
            filtered.sort(key=lambda x: x["date"] or datetime.min, reverse=True)

        # 결과 출력
        st.subheader("📊 근거 자료 (뉴스)")
        for n in filtered:
            st.markdown(
                f"""
                **{n['title']}**  
                {n['description']}  
                🗓 {n['date'].strftime('%Y-%m-%d') if n['date'] else '날짜 없음'}  
                🔗 {n['link']}
                """
            )

        # APA 참고문헌
        st.subheader("📎 참고문헌 (APA 형식, TOP 10)")
        for ref in filtered[:10]:
            st.markdown(f"- {to_apa(ref)}")
