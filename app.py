import streamlit as st
import requests
import random
import json
import re
from openai import OpenAI

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="🎬 영화 상담 추천", layout="wide")

TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w342"

GENRES = {
    "로맨스/드라마": [18, 10749],
    "액션/어드벤처": [28],
    "SF/판타지": [878, 14],
    "코미디": [35]
}

COUNTRY_MAP = {
    "전체": None,
    "한국": "KR",
    "미국": "US",
    "영어권": "US|GB|CA|AU"
}

# -----------------------------
# Session State 초기화
# -----------------------------
for key in [
    "question", "answer", "movies",
    "final_movie", "reason", "wishlist"
]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "wishlist" else []

# -----------------------------
# 사이드바
# -----------------------------
st.sidebar.header("🔑 API 설정")

tmdb_key = st.sidebar.text_input("TMDB API Key", type="password")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")

st.sidebar.divider()
st.sidebar.header("🎛️ 추천 조건")

min_rating = st.sidebar.slider("⭐ 최소 평점", 5.0, 9.0, 6.5, 0.5)
year_range = st.sidebar.slider("📅 개봉 연도", 1990, 2025, (2010, 2024))
country = st.sidebar.selectbox("🌍 국가", ["전체", "한국", "미국", "영어권"])

st.sidebar.divider()
st.sidebar.header("❤️ 찜한 영화")

if st.session_state.wishlist:
    for m in st.session_state.wishlist:
        st.sidebar.write("•", m)
else:
    st.sidebar.caption("아직 찜한 영화가 없어요")

# -----------------------------
# OpenAI Client
# -----------------------------
def get_openai_client():
    if not openai_key:
        st.error("OpenAI API Key를 입력해주세요.")
        st.stop()
    return OpenAI(api_key=openai_key)

# -----------------------------
# TMDB 영화 검색
# -----------------------------
def discover_movies(genre_ids):
    params = {
        "api_key": tmdb_key,
        "language": "ko-KR",
        "with_genres": ",".join(map(str, genre_ids)),
        "vote_average.gte": min_rating,
        "primary_release_date.gte": f"{year_range[0]}-01-01",
        "primary_release_date.lte": f"{year_range[1]}-12-31",
        "sort_by": "vote_average.desc"
    }

    country_code = COUNTRY_MAP.get(country)
    if country_code:
        params["with_origin_country"] = country_code

    movies = requests.get(
        f"{TMDB_BASE}/discover/movie",
        params=params
    ).json().get("results", [])[:5]

    # 🔥 국가 제한 fallback
    if not movies and country != "전체":
        st.info("국가 제한을 해제하고 다시 찾아볼게요 🙂")
        relaxed_params = params.copy()
        relaxed_params.pop("with_origin_country", None)

        movies = requests.get(
            f"{TMDB_BASE}/discover/movie",
            params=relaxed_params
        ).json().get("results", [])[:5]

    return movies

# -----------------------------
# 유튜브 트레일러 링크
# -----------------------------
def youtube_trailer_link(movie_id):
    res = requests.get(
        f"{TMDB_BASE}/movie/{movie_id}/videos",
        params={"api_key": tmdb_key, "language": "ko-KR"}
    ).json()

    for v in res.get("results", []):
        if v["site"] == "YouTube" and "Trailer" in v["type"]:
            return f"https://www.youtube.com/watch?v={v['key']}"
    return None

# -----------------------------
# 메인 UI
# -----------------------------
st.title("🎬 오늘의 기분으로 영화 추천")

# 1️⃣ 질문 생성
if not st.session_state.question:
    if st.button("🗨️ 상담 시작하기"):
        client = get_openai_client()
        with st.spinner("질문을 준비 중이에요..."):
            res = client.responses.create(
                model="gpt-4o-mini",
                input="영화 추천을 위한 감정 상담 질문을 하나 만들어줘. 친구처럼 짧게."
            )
            st.session_state.question = res.output_text.strip()
            st.rerun()

# 2️⃣ 사용자 답변
if st.session_state.question and not st.session_state.answer:
    st.subheader("💬 질문")
    st.markdown(f"### {st.session_state.question}")
    answer = st.text_input("당신의 답변")

    if st.button("답변 제출"):
        st.session_state.answer = answer
        st.rerun()

# 3️⃣ 영화 추천
if st.session_state.answer and not st.session_state.final_movie:
    client = get_openai_client()

    with st.spinner("당신의 마음을 이해하고 있어요..."):
        genre_prompt = f"""
        사용자의 감정에 가장 어울리는 영화 장르를 하나 골라줘.
        선택지는: {list(GENRES.keys())}
        답변: {st.session_state.answer}
        """

        genre_res = client.responses.create(
            model="gpt-4o-mini",
            input=genre_prompt
        )

        chosen_genre = next(
            (g for g in GENRES if g in genre_res.output_text),
            random.choice(list(GENRES.keys()))
        )

        movies = discover_movies(GENRES[chosen_genre])

        if not movies:
            st.error("조건에 맞는 영화를 찾지 못했어요 😢")
            st.stop()

        final_prompt = f"""
        아래 영화 중 사용자에게 가장 어울리는 하나를 골라줘.
        1~{len(movies)} 번호로 선택하고 이유도 써줘.
        {json.dumps(movies, ensure_ascii=False)}
        """

        final_res = client.responses.create(
            model="gpt-4o-mini",
            input=final_prompt
        )

        match = re.search(r"\{.*\}", final_res.output_text, re.S)
        if match:
            decision = json.loads(match.group())
            idx = decision.get("index", 1) - 1
            reason = decision.get("reason", "")
        else:
            idx = 0
            reason = "지금 기분에 가장 잘 어울리는 영화예요."

        idx = max(0, min(idx, len(movies) - 1))

        st.session_state.final_movie = movies[idx]
        st.session_state.reason = reason
        st.rerun()

# 4️⃣ 결과 화면
if st.session_state.final_movie:
    m = st.session_state.final_movie

    st.header(f"🎯 최종 추천: {m['title']}")
    st.caption(st.session_state.reason)

    cols = st.columns([1, 2])
    with cols[0]:
        st.image(POSTER_BASE + m["poster_path"])

    with cols[1]:
        st.write("⭐ 평점:", m["vote_average"])
        st.write(m["overview"])

        trailer = youtube_trailer_link(m["id"])
        if trailer:
            st.link_button("🎥 공식 트레일러 보러가기", trailer)

        if st.button("❤️ 찜하기"):
            if m["title"] not in st.session_state.wishlist:
                st.session_state.wishlist.append(m["title"])
                st.success("찜 목록에 추가했어요!")

    if st.button("🔄 다시 추천받기"):
        for k in ["question", "answer", "final_movie", "reason"]:
            st.session_state[k] = None
        st.rerun()
