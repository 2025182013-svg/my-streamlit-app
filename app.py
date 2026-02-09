# FULL UPDATED CODE WITH:
# 1) APA7 STRICT FORMAT
# 2) DATE FOLDER HISTORY
# 3) FILENAME = TOPIC BASED
# 4) STRONGER NEWS FILTERING

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


def slugify(text):
    text = re.sub(r"[^가-힣a-zA-Z0-9]+", "_", text)
    return text[:50]


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
# 뉴스 (강화 필터링)
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
            "출처": format_source(i["link"
