# FULL UPDATED CODE
# FIXES:
# 1) HISTORY DISPLAY NAME = PURE TOPIC (no _ , no .json)
# 2) INTERNAL FILE NAME SAFE, DISPLAY NAME PRETTY
# 3) SORTING BUG FIXED (관련도순 / 최신순 정상 분리)
# 4) STRONG FILTER MAINTAINED
# 5) APA7 STRICT

import streamlit as st
import requests, html, json, os, re
from datetime import datetime
from openai import OpenAI
import pandas as pd

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="RefNote AI", layout="wide")
st.title("📚 RefNote AI")
st.caption("연구 리서치 자동화 시스템 · APA7 strict · 날짜별 히스토리 · 주제기반 파일명")

HISTORY_DIR = "history"

# =====================
# 세션 상태
# =====================
if "results" not in st.session_state:
    st.session_state.results = None

# =====================
# 사이드바 API
# =====================
st.sidebar.header("🔑 API 설정")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
naver_id = st.sidebar.text_input("Naver Client ID", type="password")
naver_secret = st.sidebar.text_input("Naver Client Secret", type="password")

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


def safe_filename(text):
    return re.sub(r"[^가-힣a-zA-Z0-9]+", "_", text)[:60]

# =====================
# APA7 STRICT
# =====================
def apa_news_strict(row):
    author = row.get("출처", "Unknown")
    date_raw = row.get("발행일", "")
    try:
        dt = datetime.strptime(date_raw, "%Y-%m-%d")
        date_fmt = dt.strftime("%Y, %B %d")
    except:
        date_fmt = "n.d."
    title = row["제목"]
    source = row["출처"]
    url = row["링크"]
    return f"{author}. ({date_fmt}). {title}. {source}. {url}"

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
# 뉴스
# =====================
def search_news_korea(q):
    url = "https://openapi.naver.com/v1/search/news.json"
    headers = {
        "X-Naver-Client-Id": naver_id,
        "X-Naver-Client-Secret": naver_secret
    }
    params = {"query": q, "display": 40, "sort": "date"}
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

# =====================
# 논문 (DBpia 예정)
# =====================
def search_dbpia(q):
    return pd.DataFrame(columns=["제목", "저자", "학술지", "연도", "링크"])

# =====================
# 입력
# =====================
topic = st.text_input("연구 주제를 입력하세요")

if st.button("🔍 리서치 시작") and topic:
    with st.spinner("리서치 진행 중..."):
        questions = gen_questions(topic)
        keywords = gen_keywords(topic)
        trend = gen_trend_summary(keywords)

        news_list = []
        for k in keywords[:4]:
            news_list.extend(search_news_korea(k))

        news_list = news_list[:25]

        filtered = []
        for n in news_list:
            n["score"] = relevance(topic, n)
            if n["score"] >= 2:
                filtered.append(n)

        news_df = pd.DataFrame(filtered).drop_duplicates(subset=["링크"])
        paper_df = search_dbpia(topic)

        results = {
            "timestamp": datetime.now().isoformat(),
            "topic": topic,
            "questions": questions,
            "keywords": keywords,
            "trend": trend,
            "news": news_df.to_dict(orient="records"),
            "papers": paper_df.to_dict(orient="records")
        }

        st.session_state.results = results

        # =====================
        # 저장
        # =====================
        today = datetime.now().strftime("%Y-%m-%d")
        day_dir = os.path.join(HISTORY_DIR, today)
        os.makedirs(day_dir, exist_ok=True)

        safe_name = safe_filename(topic)
        fname = f"{safe_name}.json"

        with open(os.path.join(day_dir, fname), "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

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

    tab_news, tab_paper = st.tabs(["📰 뉴스", "📄 논문 (DBpia 예정)"])

    with tab_news:
        df = pd.DataFrame(r["news"])
        if not df.empty:
            sort = st.radio("정렬", ["관련도순", "최신순"], horizontal=True)

            if sort == "관련도순":
                df_sorted = df.sort_values(by="score", ascending=False)
            else:
                df_sorted = df.sort_values(by="발행일", ascending=False)

            st.dataframe(df_sorted, use_container_width=True)
            st.download_button("📥 뉴스 CSV 다운로드",
                df_sorted.to_csv(index=False).encode("utf-8-sig"),
                f"{r['topic']}_news.csv"
            )

            st.subheader("📎 APA 7 참고문헌 (Strict)")
            for _, row in df_sorted.head(10).iterrows():
                st.markdown(f"- {apa_news_strict(row)}")
        else:
            st.info("뉴스 결과 없음")

    with tab_paper:
        st.info("DBpia 연동 예정 영역입니다.")
        pdf = pd.DataFrame(r["papers"])
        st.dataframe(pdf, use_container_width=True)

# =====================
# 히스토리 UI
# =====================
st.sidebar.header("📂 날짜별 리서치 히스토리")

if os.path.exists(HISTORY_DIR):
    days = sorted(os.listdir(HISTORY_DIR), reverse=True)
else:
    days = []

for day in days:
    with st.sidebar.expander(f"📅 {day}"):
        day_path = os.path.join(HISTORY_DIR, day)
        files = sorted(os.listdir(day_path))
        for f in files:
            display_name = f.replace(".json", "").replace("_", " ")
            if st.button(display_name, key=f"{day}_{f}"):
                with open(os.path.join(day_path, f), "r", encoding="utf-8") as jf:
                    st.session_state.results = json.load(jf)
                st.success("리서치 복원 완료")
