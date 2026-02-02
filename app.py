import streamlit as st
import requests
import json
import re
from openai import OpenAI
from datetime import datetime

# ==================================================
# 기본 설정
# ==================================================
st.set_page_config(
    page_title="🎬 오늘의 영화 상담소",
    page_icon="🎬",
    layout="wide"
)

TMDB_IMAGE = "https://image.tmdb.org/t/p/w342"
TMDB_MOVIE_URL = "https://www.themoviedb.org/movie/"
TMDB_YOUTUBE = "https://www.youtube.com/results?search_query="

# ==================================================
# 사이드바
# ==================================================
st.sidebar.title("🔑 API 설정")

openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
tmdb_key = st.sidebar.text_input("TMDB API Key", type="password")

st.sidebar.markdown("---")
st.sidebar.subheader("🎛️ 추천 옵션")

current_year = datetime.now().year
year_range = st.sidebar.slider(
    "📅 개봉 연도",
    1990, current_year, (2010, current_year)
)

min_rating = st.sidebar.slider(
    "⭐ 최소 평점",
    0.0, 10.0, 6.5, 0.1
)

country = st.sidebar.selectbox(
    "🌍 국가",
    ["전체", "한국", "미국", "영어권"]
)

country_params = {
    "전체": {},
    "한국": {"with_original_language": "ko", "region": "KR"},
    "미국": {"with_original_language": "en", "region": "US"},
    "영어권": {"with_original_language": "en"},
}

# ==================================================
# 찜 목록
# ==================================================
if "wishlist" not in st.session_state:
    st.session_state.wishlist = []

st.sidebar.markdown("---")
st.sidebar.subheader("❤️ 찜한 영화")

if st.session_state.wishlist:
    for title in st.session_state.wishlist:
        st.sidebar.write("•", title)
else:
    st.sidebar.caption("아직 찜한 영화가 없어요")

# ==================================================
# OpenAI client (사이드바 ONLY)
# ==================================================
def get_openai_client():
    if not openai_key:
        st.error("OpenAI API Key를 사이드바에 입력해주세요.")
        st.stop()
    return OpenAI(api_key=openai_key)

# ==================================================
# 세션 상태
# ==================================================
for key in ["question", "final_movie", "reason"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ==================================================
# 제목
# ==================================================
st.title("🎬 오늘의 영화 상담소")
st.caption("지금 기분을 말해주면, 오늘 당신에게 딱 맞는 영화 하나를 골라드릴게요.")

st.markdown("<br>", unsafe_allow_html=True)

# ==================================================
# 1️⃣ 상담 질문 생성
# ==================================================
if st.session_state.question is None:
    if st.button("🗨️ 상담 시작하기"):
        client = get_openai_client()
        with st.spinner("상담 질문을 준비 중이에요..."):
            res = client.responses.create(
                model="gpt-4o-mini",
                input="영화 추천을 위한 감정 상담 질문을 하나 만들어줘. 친구에게 말하듯 짧게."
            )
            st.session_state.question = res.output_text.strip()
            st.rerun()

# ==================================================
# 2️⃣ 사용자 답변
# ==================================================
if st.session_state.question:
    st.markdown(f"### 💬 {st.session_state.question}")
    user_input = st.text_input("당신의 이야기")

    if st.button("🎬 영화 추천받기"):
        if not user_input.strip():
            st.warning("조금만 더 이야기해줘도 좋아요 🙂")
            st.stop()

        if not tmdb_key:
            st.error("TMDB API Key를 입력해주세요.")
            st.stop()

        client = get_openai_client()

        with st.spinner("당신의 마음을 이해하고 있어요..."):
            # ------------------------------
            # 1. 감정 + 장르 분석
            # ------------------------------
            analysis_prompt = f"""
            사용자의 말에 공감하고,
            어울리는 영화 장르 하나를 골라줘.

            장르 후보:
            액션, 드라마, 코미디, 로맨스, 판타지, SF

            반드시 JSON만:
            {{
              "empathy": "...",
              "genre": "드라마"
            }}

            사용자 말:
            "{user_input}"
            """

            analysis_res = client.responses.create(
                model="gpt-4o-mini",
                input=analysis_prompt
            )

            analysis_json = re.search(r"\{.*\}", analysis_res.output_text, re.S)
            analysis = json.loads(analysis_json.group())

            empathy = analysis["empathy"]
            genre = analysis["genre"]

            # ------------------------------
            # 2. TMDB 후보 영화
            # ------------------------------
            genre_id_map = {
                "액션": 28,
                "코미디": 35,
                "드라마": 18,
                "로맨스": 10749,
                "판타지": 14,
                "SF": 878
            }

            params = {
                "api_key": tmdb_key,
                "language": "ko-KR",
                "with_genres": genre_id_map.get(genre, 18),
                "sort_by": "vote_average.desc",
                "vote_average.gte": min_rating,
                "primary_release_date.gte": f"{year_range[0]}-01-01",
                "primary_release_date.lte": f"{year_range[1]}-12-31",
                "vote_count.gte": 300
            }
            params.update(country_params[country])

            movies = requests.get(
                "https://api.themoviedb.org/3/discover/movie",
                params=params
            ).json().get("results", [])[:5]

            # ------------------------------
            # 3. LLM 최종 선택 (안정화)
            # ------------------------------
            movie_text = "\n".join(
                [f"{i+1}. {m['title']}: {m.get('overview','')}" for i, m in enumerate(movies)]
            )

            final_prompt = f"""
            아래 영화 중 하나만 골라.
            숫자와 이유만 JSON으로 응답해.

            {{
              "index": 1,
              "reason": "..."
            }}

            영화 목록:
            {movie_text}
            """

            final_res = client.responses.create(
                model="gpt-4o-mini",
                input=final_prompt
            )

            match = re.search(r"\{.*\}", final_res.output_text, re.S)

            if match:
                decision = json.loads(match.group())
                idx = max(1, min(decision["index"], len(movies))) - 1
                reason = decision["reason"]
            else:
                idx = 0
                reason = "지금 기분에 가장 무난하게 어울리는 영화예요."

            st.session_state.final_movie = movies[idx]
            st.session_state.reason = empathy + " " + reason
            st.rerun()

# ==================================================
# 3️⃣ 결과 화면
# ==================================================
if st.session_state.final_movie:
    movie = st.session_state.final_movie

    st.markdown("---")
    st.markdown("## 🎯 오늘 당신을 위한 영화")

    col1, col2 = st.columns([1, 2])

    with col1:
        if movie.get("poster_path"):
            st.image(TMDB_IMAGE + movie["poster_path"], use_container_width=True)

        st.link_button(
            "🎬 영화 정보 보기",
            TMDB_MOVIE_URL + str(movie["id"])
        )

        st.link_button(
            "🎥 공식 트레일러 보러가기",
            TMDB_YOUTUBE + movie["title"] + " trailer"
        )

    with col2:
        st.markdown(f"### {movie['title']}")
        st.write(f"⭐ 평점: {movie['vote_average']}")
        st.write(movie.get("overview", "줄거리 정보가 없어요."))

        st.markdown("#### 💬 추천 이유")
        st.write(st.session_state.reason)

        if st.button("❤️ 찜하기"):
            if movie["title"] not in st.session_state.wishlist:
                st.session_state.wishlist.append(movie["title"])
                st.success("찜 목록에 추가했어요!")

    if st.button("🔄 다시 상담하기"):
        st.session_state.clear()
        st.rerun()
