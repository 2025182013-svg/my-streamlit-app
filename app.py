import streamlit as st
import requests
import json
from openai import OpenAI

# ======================
# 기본 설정
# ======================
st.set_page_config(
    page_title="🎬 오늘의 영화 상담소",
    page_icon="🎬",
    layout="wide"
)

TMDB_IMAGE = "https://image.tmdb.org/t/p/w342"
TMDB_MOVIE_URL = "https://www.themoviedb.org/movie/"

# ======================
# 사이드바
# ======================
st.sidebar.title("🔑 API 설정")

tmdb_key = st.sidebar.text_input("TMDB API Key", type="password")
openai_key = st.sidebar.text_input("OpenAI API Key", type="password")

if "wishlist" not in st.session_state:
    st.session_state.wishlist = []

st.sidebar.markdown("---")
st.sidebar.subheader("❤️ 찜한 영화")

if st.session_state.wishlist:
    for m in st.session_state.wishlist:
        st.sidebar.write("•", m)
else:
    st.sidebar.caption("아직 찜한 영화가 없어요")

# ======================
# OpenAI Client (최신)
# ======================
client = OpenAI(api_key=openai_key) if openai_key else None

# ======================
# 세션 상태
# ======================
for key in ["question", "final_movie", "reason"]:
    if key not in st.session_state:
        st.session_state[key] = None

# ======================
# 제목
# ======================
st.title("🎬 오늘의 영화 상담소")
st.caption("지금 당신의 기분을 말해주면, 딱 맞는 영화 하나를 골라드릴게요")

st.markdown("<br>", unsafe_allow_html=True)

# ======================
# 1️⃣ 상담 질문 생성
# ======================
if st.session_state.question is None:
    if st.button("🗨️ 상담 시작하기"):
        if not client:
            st.error("OpenAI API Key를 입력해주세요")
        else:
            response = client.responses.create(
                model="gpt-4.1-mini",
                input="영화 추천을 위한 감정 상담 질문을 하나 만들어줘. 친구에게 말하듯 짧게."
            )
            st.session_state.question = response.output_text
            st.rerun()

# ======================
# 2️⃣ 사용자 답변
# ======================
if st.session_state.question:
    st.markdown(f"### 💬 {st.session_state.question}")
    user_input = st.text_input("당신의 이야기")

    if st.button("🎬 영화 추천해줘"):
        if not tmdb_key or not client:
            st.error("TMDB / OpenAI API Key가 모두 필요해요")
            st.stop()

        with st.spinner("당신의 마음을 이해하는 중이에요…"):
            # ------------------
            # 감정 + 장르 분석
            # ------------------
            analysis_prompt = f"""
            사용자의 말을 보고 감정을 공감하고,
            어울리는 영화 장르 1개를 골라줘.

            장르 후보:
            액션, 드라마, 코미디, 판타지, SF, 로맨스

            반드시 JSON으로만 답해:
            {{
              "genre": "드라마",
              "empathy": "오늘 많이 힘들었겠어요."
            }}

            사용자 말:
            "{user_input}"
            """

            analysis_res = client.responses.create(
                model="gpt-4.1-mini",
                input=analysis_prompt
            )

            analysis = json.loads(analysis_res.output_text)
            genre = analysis["genre"]
            empathy = analysis["empathy"]

            genre_id_map = {
                "액션": 28,
                "코미디": 35,
                "드라마": 18,
                "SF": 878,
                "로맨스": 10749,
                "판타지": 14,
            }

            genre_id = genre_id_map.get(genre, 18)

            # ------------------
            # TMDB 후보 영화
            # ------------------
            discover_url = (
                f"https://api.themoviedb.org/3/discover/movie"
                f"?api_key={tmdb_key}"
                f"&language=ko-KR"
                f"&with_genres={genre_id}"
                f"&sort_by=vote_average.desc"
            )

            candidates = requests.get(discover_url).json().get("results", [])[:5]

            movie_text = "\n".join(
                [f"{i+1}. {m['title']}: {m.get('overview','')}" for i, m in enumerate(candidates)]
            )

            # ------------------
            # LLM 최종 선택
            # ------------------
            final_prompt = f"""
            사용자 감정:
            {user_input}

            후보 영화:
            {movie_text}

            이 중 단 하나만 골라.
            반드시 JSON으로:
            {{
              "index": 1,
              "reason": "이 영화가 위로가 될 것 같아요."
            }}
            """

            final_res = client.responses.create(
                model="gpt-4.1-mini",
                input=final_prompt
            )

            decision = json.loads(final_res.output_text)

            st.session_state.final_movie = candidates[decision["index"] - 1]
            st.session_state.reason = empathy + " " + decision["reason"]

            st.rerun()

# ======================
# 3️⃣ 결과 화면
# ======================
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
        st.write(f"⭐ {movie['vote_average']}")
        st.write(movie.get("overview", "줄거리 정보 없음"))

        st.markdown("#### 💬 추천 이유")
        st.write(st.session_state.reason)

        if st.button("❤️ 찜하기"):
            if movie["title"] not in st.session_state.wishlist:
                st.session_state.wishlist.append(movie["title"])
                st.success("찜 목록에 추가했어요!")

    if st.button("🔄 다시 상담하기"):
        st.session_state.clear()
        st.rerun()
