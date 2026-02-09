import streamlit as st
import requests, html, json, os
from datetime import datetime
from openai import OpenAI
import pandas as pd

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="RefNote AI", layout="wide")
st.title("📚 RefNote AI")
st.caption("연구/뉴스 분리형 리서치 생성 시스템 · APA7 · 히스토리 복원 · CSV 다운로드")

HISTORY_FILE = "history.json"

# =====================
# 세션 상태
# =====================
if "results" not in st.session_state:
    st.session_state.results = None
if "history" not in st.session_state:
    st.session_state.history = []

# =====================
# 사이드바 API
# =====================
st.sidebar.header("🔑 API 설정")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
naver_id = st.sidebar.text_input("Naver Client ID", type="password")
naver_secret = st.sidebar.text_input("Naver Client Secret", type="password")
newsapi_key = st.sidebar.text_input("NewsAPI Key (글로벌 뉴스, 선택)", type="password")

if not openai_key:
    st.warning("⬅️ OpenAI API Key 필수")
    st.stop()

client = OpenAI(api_key=openai_key)

# =====================
# 유틸
# =====================
def clean(t):
    return html.unescape(t).replace("<b>", "").replace("</b>", "").strip()


def parse_date(d):
    try:
        return datetime.strptime(d, "%a, %d %b %Y %H:%M:%S %z")
    except:
        return None


def format_source(domain):
    return domain.replace("www.", "").split(".")[0].capitalize()


def apa_news(row):
    author = row.get("저자", row.get("출처", "Unknown"))
    year = row.get("발행일", "")[:4] if row.get("발행일") else "n.d."
    return f"{author}. ({year}). {row['제목']}. {row['출처']}. {row['링크']}"

# =====================
# AI
# =====================
def gen_questions(topic):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"다음 주제에 대한 연구 질문 3개 생성:\n{topic}"}],
        temperature=0.3
    )
    return [q.strip("-• ") for q in r.choices[0].message.content.split("\n") if q.strip()]


def gen_keywords(topic):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"다음 주제 핵심 키워드 5개를 중요도순 쉼표 출력:\n{topic}"}],
        temperature=0.2
    )
    return [k.strip() for k in r.choices[0].message.content.split(",")]


def gen_trend_summary(keywords):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"키워드 기반 최신 연구동향 요약:\n{', '.join(keywords)}"}],
        temperature=0.2
    )
    return r.choices[0].message.content.strip()


def relevance(topic, n):
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"연구주제:{topic}\n제목:{n['제목']}\n요약:{n['요약']}\n관련도 0~3 숫자만"}],
        temperature=0
    )
    try:
        return int(r.choices[0].message.content.strip())
    except:
        return 0

# =====================
# 분류기
# =====================
def classify_topic(topic):
    if any(k in topic for k in ["비교", "vs", "정책", "제도", "국가", "모델"]):
        return "research"
    return "news"

# =====================
# 뉴스
# =====================
def search_news_korea(q):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {"X-Naver-Client-Id": naver_id, "X-Naver-Client-Secret": naver_secret}
    params = {"query": q, "display": 30, "sort": "date"}
    r = requests.get(url, headers=headers, params=params).json()
    out = []
    for i in r.get("items", []):
        out.append({
            "제목": clean(i["title"]),
            "요약": clean(i["description"]),
            "출처": format_source(i["link"].split("/")[2]),
            "발행일": parse_date(i["pubDate"]).strftime("%Y-%m-%d") if parse_date(i["pubDate"]) else "",
            "링크": i["link"]
        })
    return out


def search_news_global(q):
    if not newsapi_key:
        return []
    url = "https://newsapi.org/v2/everything"
    params = {"q": q, "language": "en", "sortBy": "publishedAt", "pageSize": 30, "apiKey": newsapi_key}
    r = requests.get(url, params=params).json()
    out = []
    for i in r.get("articles", []):
        out.append({
            "제목": i.get("title"),
            "요약": i.get("description"),
            "출처": i.get("source", {}).get("name", "NewsAPI"),
            "발행일": i.get("publishedAt", "")[:10],
            "링크": i.get("url")
        })
    return out

# =====================
# 논문 (CrossRef)
# =====================
def search_crossref(q):
    url = "https://api.crossref.org/works"
    params = {"query": q, "rows": 20}
    r = requests.get(url, params=params).json()
    out = []
    for i in r.get("message", {}).get("items", []):
        out.append({
            "제목": i.get("title", [""])[0],
            "저자": ", ".join([f"{a.get('family','')} {a.get('given','')}" for a in i.get("author", [])]),
            "학술지": i.get("container-title", [""])[0],
            "연도": i.get("published-print", {}).get("date-parts", [[""]])[0][0] if i.get("published-print") else "",
            "링크": i.get("URL")
        })
    return pd.DataFrame(out)

# =====================
# 입력
# =====================
topic = st.text_input("연구 주제를 입력하세요")

if st.button("🔍 리서치 시작") and topic:
    with st.spinner("리서치 진행 중..."):
        mode = classify_topic(topic)
        questions = gen_questions(topic)
        keywords = gen_keywords(topic)
        trend = gen_trend_summary(keywords)

        news_list = []
        if mode == "news":
            for k in keywords[:2]:
                news_list.extend(search_news_korea(k))
        else:
            for k in keywords[:2]:
                news_list.extend(search_news_global(k))
                news_list.extend(search_news_korea(k))

        filtered = []
        for n in news_list:
            n["score"] = relevance(topic, n)
            if n["score"] >= 2:
                filtered.append(n)

        news_df = pd.DataFrame(filtered).drop_duplicates(subset=["링크"])
        paper_df = search_crossref(topic)

        st.session_state.results = {
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "mode": mode,
            "questions": questions,
            "keywords": keywords,
            "trend": trend,
            "news": news_df.to_dict(orient="records"),
            "papers": paper_df.to_dict(orient="records")
        }

        # 히스토리 저장
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                st.session_state.history = json.load(f)

        st.session_state.history.append(st.session_state.results)
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(st.session_state.history, f, ensure_ascii=False, indent=2)

# =====================
# 출력
# =====================
if st.session_state.results:
    r = st.session_state.results

    st.subheader("🔍 연구 질문")
    for q in r["questions"]:
        st.markdown(f"• {q}")

    st.subheader("🔑 핵심 키워드")
    st.write(", ".join(r["keywords"]))

    st.subheader("📈 연구 동향")
    st.markdown(r["trend"])

    tab_news, tab_paper = st.tabs(["📰 뉴스", "📄 논문"])

    with tab_news:
        df = pd.DataFrame(r["news"])
        if not df.empty:
            sort = st.radio("정렬", ["관련도순", "최신순"], horizontal=True)
            if sort == "관련도순":
                df = df.sort_values(by="score", ascending=False)
            else:
                df = df.sort_values(by="발행일", ascending=False)
            st.dataframe(df, use_container_width=True)
            st.download_button("📥 뉴스 CSV", df.to_csv(index=False).encode("utf-8-sig"), f"{r['topic']}_news.csv")

            st.subheader("📎 APA 참고문헌 (Top10)")
            for _, row in df.head(10).iterrows():
                st.markdown(f"- {apa_news(row)}")
        else:
            st.info("뉴스 결과 없음")

    with tab_paper:
        pdf = pd.DataFrame(r["papers"])
        st.dataframe(pdf, use_container_width=True)
        st.download_button("📥 논문 CSV", pdf.to_csv(index=False).encode("utf-8-sig"), f"{r['topic']}_papers.csv")

# =====================
# 히스토리
# =====================
st.sidebar.header("📂 리서치 히스토리")
if os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        saved = json.load(f)
else:
    saved = []

for h in reversed(saved):
    if st.sidebar.button(f"{h['topic']} ({h['timestamp'][:10]})"):
        st.session_state.results = h
        st.success("리서치 복원 완료")
