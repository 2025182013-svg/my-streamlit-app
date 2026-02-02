import streamlit as st
import requests
import random
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
st.sidebar.subheader("❤️ 내가 찜한 영화")

if st.session_state.wishlist:
    for m in st.session_state.wishlist:
        st.sidebar.write("•", m)
else:
    st.sidebar.caption("아직 찜한 영화가 없어요")

# ======================
# OpenAI Client
# ======================
client = OpenAI(api_key=openai_key) if openai_key else None

# ======================
# 세션 상태
# ======================
if "question" not in st.session_state:
    st.session_state.question = None
if "user_answer" not in st.session_state:
    st.session_state.user_answer = ""
if "final_movie" not in st.session_state:
    st.session_state.final_movie = None
if "reason" not in st.session_state:
    st.session_state.reason = None

# ======================
# 제목
# ======================
st.title("🎬 오늘의 영화 상담소")
st.caption("지금 당신의 마음 상태에 어울리는 영화를 추천해드릴게요")

st.markdown("<br>", unsafe_allow_html=True)

# ======================
# 1️⃣ 상담 질문 생성
# ======================
if st.session_state.question is None:
    if st.button("🗨️ 상담 시작하기"):
        if not client:
            st.error("OpenAI API Key가 필요해요!")
        else:
            q_prompt = """
            영화 추천을 위한 감정 상담 질문을 하나 만들어줘.
            너무 길지 않고 친구에게 말하듯 자연스럽게.
            """
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": q_prompt}]
            )
            st.session_state.question = res.choices[0].message.content.strip()
            st.rerun()

# ======================
# 2️⃣ 사용자 답변
# ======================
if st.session_state.question:
    st.markdown(f"### 💬 {st.session_state.question}")
    user_input = st.text_input("당신의 이야기", value=st.session_state.user_answer)

    if st.button("🎬 영화 추천해줘"):
        st.session_state.user_answer = user_input

        if not tmdb_key or not client:
            st.error("TMDB / OpenAI API Key가 모두 필요해요")
            st.stop()

        with st.spinner("당신의 마음을 분석 중이에요…"):
            # ------------------
            # 감정 분석 + 장르 추출
            # ------------------
            analysis_prompt = f"""
            사용자의 말에서 감정 상태와 어울리는 영화 장르 1~2개를 추출해줘.
            장르는 액션, 드라마, 코미디, 판타지, SF, 로맨스 중에서.
            그리고 사용자에게 공감하는 한 문장도 만들어줘.

            사용자 말:
            "{user_input}"

            JSON 형식으로:
            {{
              "emotion_summary": "...",
              "genres": ["드라마", "판타지"]
            }}
            """

            analysis = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": analysis_prompt}]
            )

            result = eval(analysis.choices[0].message.content)
            genres = result["genres"]

            genre_id_map = {
                "액션": 28,
                "코미디": 35,
                "드라마": 18,
                "SF": 878,
                "로맨스": 10749,
                "판타지": 14,
            }

            genre_id = genre_id_map.get(genres[0], 18)

            # ------------------
            # TMDB 후보 영화
            # ------------------
            url = (
                f"https://api.themoviedb.org/3/discover/movie"
                f"?api_key={tmdb_key}"
                f"&language=ko-KR"
                f"&with_genres={genre_id}"
                f"&sort_by=vote_average.desc"
            )
            candidates = requests.get(url).json().get("results", [])[:6]

            # ------------------
            # LLM 최종 선택
            # ------------------
            movie_list_text = "\n".join([
                f"{i+1}. {m['title']}: {m.get('overview','')}"
                for i, m in enumerate(candidates)
            ])

            final_prompt = f"""
            사용자의 감정과 상황을 고려해서
            아래 영화 중 단 하나만 골라줘.
            그리고 왜 이 영화를 추천하는지 설명해줘.

            사용자 상태:
            {user_input}

            후보 영화:
            {movie_list_text}

            JSON 형식:
            {{
              "index": 1,
              "reason": "..."
            }}
            """

            final = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": final_prompt}]
            )

            decision = eval(final.choices[0].message.content)
            st.session_state.final_movie = candidates[decision["index"] - 1]
            st.session_state.reason = decision["reason"]

            st.rerun()

# ======================
# 3️⃣ 최종 결과
# ======================
if st.session_state.final_movie:
    movie = st.session_state.final_movie

    st.markdown("---")
    st.markdown("## 🎯 오늘 당신을 위한 영화")

    col1, col2 = st.columns([1, 2])

    with col1:
        if movie.get("poster_path"):
            st.image(
                TMDB_IMAGE + movie["poster_path"],
                use_container_width=True
            )
        st.link_button(
            "🎬 영화 상세 보기",
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
