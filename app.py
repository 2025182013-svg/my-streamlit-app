import streamlit as st
import requests
import json
import time
from openai import OpenAI

# =====================
# 기본 설정
# =====================
st.set_page_config(page_title="🎬 오늘의 기분 영화 추천", layout="wide")

TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w342"

GENRE_IDS = {
    "액션": 28,
    "코미디": 35,
    "SF": 878,
    "드라마": 18,
    "로맨스": 10749,
    "판타지": 14
}

MOOD_KEYWORDS = {
    "액션": "action adventure energy",
    "로맨스": "romantic sunset love",
    "SF": "space galaxy stars",
    "코미디": "happy fun colorful",
    "드라마": "emotional rain cinematic",
    "판타지": "fantasy magical forest"
}

# =====================
# 사이드바
# =====================
st.sidebar.header("🔑 API 키 입력")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
tmdb_key = st.sidebar.text_input("TMDB API Key", type="password")
unsplash_key = st.sidebar.text_input("Unsplash Access Key", type="password")

# =====================
# 세션 상태
# =====================
if "done" not in st.session_state:
    st.session_state.done = False

# =====================
# OpenAI: 감정 → 장르
# =====================
def analyze_emotion(text):
    client = OpenAI(api_key=openai_key)

    prompt = f"""
사용자의 오늘 기분을 바탕으로
가장 어울리는 영화 장르 하나를 골라주세요.

선택 가능 장르:
액션, 코미디, SF, 드라마, 로맨스, 판타지

JSON 형식으로만 답변:
{{
  "genre": "...",
  "personality": "성향 설명 (2~3문장)"
}}

사용자 기분:
{text}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return json.loads(res.choices[0].message.content)

# =====================
# TMDB 영화
# =====================
def get_movies(genre):
    params = {
        "api_key": tmdb_key,
        "language": "ko-KR",
        "with_genres": GENRE_IDS[genre],
        "sort_by": "popularity.desc"
    }
    res = requests.get(f"{TMDB_BASE}/discover/movie", params=params)
    return res.json().get("results", [])[:3]

# =====================
# Unsplash 이미지
# =====================
def get_mood_image(genre):
    params = {
        "query": MOOD_KEYWORDS[genre],
        "client_id": unsplash_key,
        "per_page": 1
    }
    res = requests.get("https://api.unsplash.com/search/photos", params=params)
    data = res.json()
    if data.get("results"):
        return data["results"][0]["urls"]["regular"]
    return None

# =====================
# ZenQuotes
# =====================
def get_quote():
    res = requests.get("https://zenquotes.io/api/random")
    q = res.json()[0]
    return q["q"], q["a"]

# =====================
# OpenAI 해석 스트리밍
# =====================
def stream_ai_analysis(user_text, movie, quote):
    client = OpenAI(api_key=openai_key)

    prompt = f"""
사용자 기분:
{user_text}

추천 영화:
{movie['title']} - {movie['overview']}

명언:
"{quote[0]}"

요구사항:
1. 사용자 성향 설명 (2문장)
2. 이 영화를 추천한 이유 (1문장)
3. 명언을 사용자에게 맞게 해석 (1문장)
"""

    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        stream=True
    )

    placeholder = st.empty()
    text = ""

    for chunk in stream:
        if chunk.choices[0].delta.get("content"):
            text += chunk.choices[0].delta.content
            placeholder.markdown(text)
            time.sleep(0.02)

# =====================
# 메인 화면
# =====================
st.title("🎬 오늘의 기분으로 영화 추천받기")
st.caption("기분을 말해주면, AI가 딱 맞는 영화를 골라줘요")

if not st.session_state.done:
    mood = st.text_area("💬 오늘 기분이 어때요?", placeholder="예: 아무것도 하기 싫고 좀 우울해요")

    if st.button("🎯 추천받기"):
        if not (openai_key and tmdb_key and unsplash_key):
            st.error("사이드바에 모든 API 키를 입력해주세요.")
            st.stop()

        with st.spinner("AI가 당신의 마음을 이해하는 중..."):
            analysis = analyze_emotion(mood)
            genre = analysis["genre"]
            movies = get_movies(genre)
            image = get_mood_image(genre)
            quote = get_quote()

        st.session_state.result = {
            "mood": mood,
            "analysis": analysis,
            "movies": movies,
            "image": image,
            "quote": quote
        }
        st.session_state.done = True
        st.rerun()

# =====================
# 결과 화면
# =====================
else:
    r = st.session_state.result

    st.header(f"🎭 당신에게 딱인 장르는 **{r['analysis']['genre']}**")

    st.info(r["analysis"]["personality"])

    st.divider()

    st.subheader("🍿 추천 영화")
    cols = st.columns(3)
    for col, m in zip(cols, r["movies"]):
        with col:
            if m.get("poster_path"):
                st.image(POSTER_BASE + m["poster_path"])
            st.markdown(f"**{m['title']}**")
            st.write("⭐", m["vote_average"])

    st.divider()

    if r["image"]:
        st.subheader("🎨 오늘의 무드")
        st.image(r["image"], use_container_width=True)

    st.subheader("💬 오늘의 한마디")
    st.markdown(f"*{r['quote'][0]}*  \n— {r['quote'][1]}")

    st.divider()

    st.subheader("🤖 AI의 최종 해석")
    stream_ai_analysis(r["mood"], r["movies"][0], r["quote"])

    if st.button("🔁 다시 해보기"):
        st.session_state.clear()
        st.rerun()
