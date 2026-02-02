import streamlit as st
import requests
import time
from openai import OpenAI

# =============================
# 기본 설정
# =============================
st.set_page_config(page_title="🎬 AI 영화 추천", layout="wide")

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

GENRE_ICONS = {
    "액션": "🔥",
    "코미디": "😂",
    "SF": "🚀",
    "드라마": "🎭",
    "로맨스": "💖",
    "판타지": "🧙‍♂️"
}

GENRE_MOOD_KEYWORDS = {
    "액션": "action adventure energy",
    "로맨스": "romantic sunset love",
    "SF": "space galaxy stars",
    "코미디": "happy fun colorful",
    "드라마": "emotional rain cinematic",
    "판타지": "fantasy magical forest"
}

# =============================
# Session State
# =============================
for k in ["answer", "result"]:
    if k not in st.session_state:
        st.session_state[k] = None

# =============================
# 사이드바
# =============================
st.sidebar.header("🔑 API 설정")
tmdb_key = st.sidebar.text_input("TMDB API Key", type="password")
unsplash_key = st.sidebar.text_input("Unsplash Access Key", type="password")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")

st.sidebar.divider()
genre = st.sidebar.selectbox("🎭 오늘의 장르", list(GENRE_IDS.keys()))

# =============================
# CSS
# =============================
st.markdown("""
<style>
.movie-card {
    background: white;
    border-radius: 16px;
    padding: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}
.callout {
    background-color: #e8f1ff;
    padding: 20px;
    border-radius: 16px;
}
.quote {
    font-style: italic;
    font-size: 0.9rem;
    color: #444;
}
</style>
""", unsafe_allow_html=True)

# =============================
# Unsplash
# =============================
def get_mood_image(genre):
    query = GENRE_MOOD_KEYWORDS.get(genre, "movie mood")
    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "client_id": unsplash_key,
        "per_page": 1,
        "orientation": "landscape"
    }
    res = requests.get(url, params=params)
    data = res.json()
    if data.get("results"):
        return data["results"][0]["urls"]["regular"]
    return None

# =============================
# 통합 결과
# =============================
def get_complete_result():
    result = {}

    # TMDB
    tmdb_res = requests.get(
        f"{TMDB_BASE}/discover/movie",
        params={
            "api_key": tmdb_key,
            "language": "ko-KR",
            "with_genres": GENRE_IDS[genre],
            "sort_by": "popularity.desc"
        }
    ).json()

    result["movies"] = tmdb_res.get("results", [])[:3]

    # Unsplash
    result["mood_image"] = get_mood_image(genre)

    # ZenQuotes
    quote = requests.get("https://zenquotes.io/api/random").json()[0]
    result["quote"] = quote

    return result

# =============================
# OpenAI 스트리밍 해석
# =============================
def stream_ai_analysis(answer, movies, quote):
    client = OpenAI(api_key=openai_key)

    prompt = f"""
사용자 답변: {answer}

1. 성향 분석 2~3문장
2. 아래 영화들을 왜 추천하는지 1~2문장
3. 명언 "{quote['q']}"을 사용자 성향에 맞게 해석 1문장

영화 목록:
{[m['title'] for m in movies]}
"""

    stream = client.responses.stream(
        model="gpt-4o-mini",
        input=prompt
    )

    text = ""
    placeholder = st.empty()

    for event in stream:
        if event.type == "response.output_text.delta":
            text += event.delta
            placeholder.markdown(text)
            time.sleep(0.02)

    return text

# =============================
# UI
# =============================
st.title("🎬 AI 감정 기반 영화 추천")

if not st.session_state.answer:
    st.subheader("💬 오늘 기분은 어때요?")
    st.session_state.answer = st.text_input("자유롭게 적어주세요")

if st.button("🎯 결과 보기"):
    if not (tmdb_key and unsplash_key and openai_key):
        st.error("모든 API 키를 입력해주세요.")
        st.stop()

    with st.spinner("결과를 분석 중이에요..."):
        result = get_complete_result()
        st.session_state.result = result

# =============================
# 결과 화면
# =============================
if st.session_state.result:
    r = st.session_state.result

    st.divider()
    icon = GENRE_ICONS.get(genre, "🎬")
    st.header(f"{icon} 당신에게 딱인 장르는 {genre}!")

    # AI 분석
    with st.container():
        st.markdown('<div class="callout">', unsafe_allow_html=True)
        st.subheader("🤖 AI 분석 결과")
        stream_ai_analysis(
            st.session_state.answer,
            r["movies"],
            r["quote"]
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # 영화 카드
    st.subheader("🍿 추천 영화")
    cols = st.columns(3)

    for col, m in zip(cols, r["movies"]):
        with col:
            st.markdown('<div class="movie-card">', unsafe_allow_html=True)
            if m.get("poster_path"):
                st.image(POSTER_BASE + m["poster_path"])
            st.markdown(f"**{m['title']}**")
            st.write("⭐", m["vote_average"])

            with st.expander("상세 정보"):
                st.write(m["overview"])
            st.markdown("</div>", unsafe_allow_html=True)

    st.divider()

    # 분위기
    st.subheader("🎨 오늘의 무드")
    if r["mood_image"]:
        st.image(r["mood_image"], use_container_width=True)

    # 명언
    st.subheader("💬 오늘의 명언")
    st.markdown(
        f"""
        <div class="quote">
        “{r['quote']['q']}”  
        <br/>— {r['quote']['a']}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.divider()

    # 하단 버튼
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 다시 테스트하기"):
            st.session_state.answer = None
            st.session_state.result = None
            st.rerun()
    with col2:
        st.button("📤 결과 공유하기")
