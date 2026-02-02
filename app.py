import streamlit as st
import requests
from collections import Counter
import datetime
import time

# ----------------------
# 기본 설정
# ----------------------
st.set_page_config(
    page_title="🎬 나와 어울리는 영화는?",
    page_icon="🎬",
    layout="wide"
)

TMDB_IMAGE = "https://image.tmdb.org/t/p/w342"

# ----------------------
# 사이드바: TMDB + 필터
# ----------------------
st.sidebar.title("🎛 추천 설정")

api_key = st.sidebar.text_input("TMDB API Key", type="password")

current_year = datetime.datetime.now().year

year_range = st.sidebar.slider(
    "📅 개봉 연도 범위",
    min_value=1990,
    max_value=current_year,
    value=(2010, current_year)
)

min_rating = st.sidebar.slider(
    "⭐ 최소 평점",
    min_value=0.0,
    max_value=10.0,
    value=6.5,
    step=0.1
)

st.sidebar.markdown("---")
st.sidebar.caption("필터를 조절하면 추천 영화가 달라져요 🍿")

# ----------------------
# Session State
# ----------------------
if "step" not in st.session_state:
    st.session_state.step = 0
if "answers" not in st.session_state:
    st.session_state.answers = {}

# ----------------------
# 질문 (조금 더 재미있게 수정)
# ----------------------
questions = [
    (
        "하루가 끝났을 때, 당신의 머릿속은 어떤 상태인가요?",
        [
            "오늘 하루 있었던 감정들이 계속 떠오른다",
            "아직 에너지가 남아서 뭐라도 하고 싶다",
            "현실 말고 다른 세계로 도망가고 싶다",
            "아무 생각 없이 웃고 싶다",
        ],
    ),
    (
        "시험이나 큰 일정이 끝난 직후, 가장 먼저 드는 생각은?",
        [
            "이제야 마음이 좀 정리되는 느낌",
            "지금부터가 진짜 시작이다!",
            "한 단계 성장한 기분이 든다",
            "일단 웃긴 거부터 보고 싶다",
        ],
    ),
    (
        "영화를 보러 간다면, 당신이 더 끌리는 분위기는?",
        [
            "현실적이고 공감 가는 이야기",
            "속도감 있고 손에 땀 나는 전개",
            "상상력을 자극하는 세계관",
            "편하게 웃으면서 볼 수 있는 분위기",
        ],
    ),
    (
        "친구가 갑자기 영화를 보자고 한다면?",
        [
            "여운 남는 영화면 좋겠어",
            "재밌고 시원한 거!",
            "현실 잊게 해주는 영화",
            "아무 생각 없이 웃을 수 있는 영화",
        ],
    ),
    (
        "영화 한 편을 보고 난 뒤, 가장 중요하게 남는 건?",
        [
            "감정과 메시지",
            "장면 하나하나의 임팩트",
            "세계관과 설정",
            "얼마나 웃었는지",
        ],
    ),
]

genre_by_choice = {
    0: "드라마",
    1: "액션",
    2: "판타지",
    3: "코미디",
}

genre_id_map = {
    "액션": 28,
    "코미디": 35,
    "드라마": 18,
    "SF": 878,
    "로맨스": 10749,
    "판타지": 14,
}

# ----------------------
# 제목
# ----------------------
st.title("🎬 나와 어울리는 영화는?")
st.caption("간단한 질문으로 지금 당신의 영화 취향을 알아보세요 ✨")

st.markdown("<br>", unsafe_allow_html=True)

# ----------------------
# 질문 진행 화면
# ----------------------
if st.session_state.step < len(questions):

    q, options = questions[st.session_state.step]

    st.markdown(f"## Q{st.session_state.step + 1}")
    st.markdown(f"### {q}")

    st.markdown("<br>", unsafe_allow_html=True)

    choice = st.radio("", options, key=f"q_{st.session_state.step}")

    st.markdown("<br><br>", unsafe_allow_html=True)

    if st.button("👉 다음"):
        st.session_state.answers[st.session_state.step] = options.index(choice)
        st.session_state.step += 1
        st.rerun()

# ----------------------
# 로딩 화면
# ----------------------
elif st.session_state.step == len(questions):
    with st.spinner("취향을 분석하고 있어요... 🎬"):
        time.sleep(1.5)
        st.session_state.step += 1
        st.rerun()

# ----------------------
# 결과 화면
# ----------------------
else:
    if not api_key:
        st.error("TMDB API Key를 입력해주세요.")
        st.stop()

    # 장르 분석
    counts = Counter(st.session_state.answers.values())
    top_idx = counts.most_common(1)[0][0]
    selected_genre = genre_by_choice[top_idx]
    genre_id = genre_id_map[selected_genre]

    st.markdown(f"## 🎯 당신에게 딱인 장르는 **{selected_genre}**!")

    # Discover API (투표수 조건 제거)
    discover_url = (
        f"https://api.themoviedb.org/3/discover/movie"
        f"?api_key={api_key}"
        f"&language=ko-KR"
        f"&with_genres={genre_id}"
        f"&primary_release_date.gte={year_range[0]}-01-01"
        f"&primary_release_date.lte={year_range[1]}-12-31"
        f"&vote_average.gte={min_rating}"
        f"&sort_by=vote_average.desc"
    )

    movies = requests.get(discover_url).json().get("results", [])[:6]

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🍿 추천 영화")

    cols = st.columns(3)

    for i, movie in enumerate(movies):
        with cols[i % 3]:
            if movie.get("poster_path"):
                st.image(TMDB_IMAGE + movie["poster_path"], use_container_width=True)

            st.markdown(f"**{movie['title']}**")
            st.write(f"⭐ {movie['vote_average']}")

            with st.expander("상세 정보"):
                st.write(movie.get("overview", "줄거리 정보 없음"))

                # 트레일러
                video_url = (
                    f"https://api.themoviedb.org/3/movie/{movie['id']}/videos"
                    f"?api_key={api_key}&language=ko-KR"
                )
                videos = requests.get(video_url).json().get("results", [])

                trailer = next(
                    (v for v in videos if v["site"] == "YouTube" and v["type"] == "Trailer"),
                    None
                )

                if trailer:
                    st.link_button(
                        "🎥 공식 트레일러 보러가기",
                        f"https://www.youtube.com/watch?v={trailer['key']}"
                    )

    st.markdown("---")
    if st.button("🔄 다시 테스트하기"):
        st.session_state.clear()
        st.rerun()
