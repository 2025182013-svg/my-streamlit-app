import streamlit as st
import requests
import json
from openai import OpenAI

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

# ==================================================
# 사이드바 (무조건 입력)
# ==================================================
st.sidebar.title("🔑 API 설정")

openai_key = st.sidebar.text_input(
    "OpenAI API Key",
    type="password",
    help="sk- 로 시작하는 OpenAI API Key"
)

tmdb_key = st.sidebar.text_input(
    "TMDB API Key",
    type="password"
)

st.sidebar.markdown("---")

# ==================================================
# 찜 목록
# ==================================================
if "wishlist" not in st.session_state:
    st.session_state.wishlist = []

st.sidebar.subheader("❤️ 찜한 영화")
if st.session_state.wishlist:
    for title in st.session_state.wishlist:
        st.sidebar.write("•", title)
else:
    st.sidebar.caption("아직 찜한 영화가 없어요")

# ==================================================
# OpenAI client 생성 함수 (⭐ 핵심)
# ==================================================
def get_openai_client():
    if not openai_key:
        st.error("⚠️ OpenAI API Key를 사이드바에 입력해주세요.")
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
            try:
                res = client.responses.create(
                    model="gpt-4o-mini",
                    input="영화 추천을 위한 감정 상담 질문을 하나 만들어줘. 친구에게 말하듯 짧게."
                )
                st.session_state.question = res.output_text.strip()
                st.rerun()
            except Exception as e:
                st.error("OpenAI API 인증에 실패했어요.")
                st.caption(str(e))
                st.stop()

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
            # --------------------------------------
            # 1. 감정 공감 + 장르 결정
            # --------------------------------------
            analysis_prompt = f"""
            사용자의 말을 보고 공감 한 문장과
            어울리는 영화 장르 1개를 골라줘.

            장르 후보:
            액션, 드라마, 코미디, 로맨스, 판타지, SF

            반드시 JSON으로만 응답해.
            {{
              "empathy": "공감 문장",
              "genre": "드라마"
            }}

            사용자 말:
            "{user_input}"
            """

            try:
                analysis_res = client.responses.create(
                    model="gpt-4o-mini",
                    input=analysis_prompt
                )
                analysis = json.loads(analysis_res.output_text)
            except Exception as e:
                st.error("감정 분석 중 오류가 발생했어요.")
                st.caption(str(e))
                st.stop()

            empathy = analysis["empathy"]
            genre = analysis["genre"]

            # --------------------------------------
            # 2. TMDB 후보 영화 수집
            # --------------------------------------
            genre_id_map = {
                "액션": 28,
                "코미디": 35,
                "드라마": 18,
                "로맨스": 10749,
                "판타지": 14,
                "SF": 878
            }

            genre_id = genre_id_map.get(genre, 18)

            discover_url = (
                f"https://api.themoviedb.org/3/discover/movie"
                f"?api_key={tmdb_key}"
                f"&language=ko-KR"
                f"&with_genres={genre_id}"
                f"&sort_by=vote_average.desc"
                f"&vote_count.gte=300"
            )

            movies = requests.get(discover_url).json().get("results", [])[:5]

            movie_text = "\n".join(
                [f"{i+1}. {m['title']}: {m.get('overview','')}" for i, m in enumerate(movies)]
            )

            # --------------------------------------
            # 3. LLM 최종 1편 선택
            # --------------------------------------
            final_prompt = f"""
            사용자 감정:
            {user_input}

            후보 영화 목록:
            {movie_text}

            이 중 단 하나만 골라.
            반드시 JSON으로만 응답해.
            {{
              "index": 1,
              "reason": "추천 이유"
            }}
            """

            try:
                final_res = client.responses.create(
                    model="gpt-4o-mini",
                    input=final_prompt
                )
                decision = json.loads(final_res.output_text)
            except Exception as e:
                st.error("최종 추천 중 오류가 발생했어요.")
                st.caption(str(e))
                st.stop()

            st.session_state.final_movie = movies[decision["index"] - 1]
            st.session_state.reason = empathy + " " + decision["reason"]

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
            "🎬 영화 상세 페이지",
            TMDB_MOVIE_URL + str(movie["id"])
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
