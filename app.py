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

# ✅ 국가 설정 추가
country_option = st.sidebar.selectbox(
    "🌍 영화 국가",
    [
        "한국",
        "미국 (헐리우드)",
        "영어권 전체",
        "전체",
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("국가를 제한하면 이상한(?) 영화가 확 줄어요 😄")

# ----------------------
# 국가 옵션 매핑
# ----------------------
country_params = {
    "한국": {
        "region": "KR",
        "with_original_language": "ko",
    },
    "미국 (헐리우드)": {
        "region": "US",
        "with_original_language": "en",
    },
    "영어권 전체": {
        "with_original_language": "en",
    },
    "전체": {}
}

# ----------------------
# Session State
# ----------------------
if "step" not in st.session_state:
    st.session_state.step = 0
if "answers" not in st.session_state:
    st.session_state.answers = {}

# ----------------------
# 질문
# ----------------------
questions = [
    (
        "하루가 끝났을 때, 당신의 머릿속은?",
        [
            "오늘 있었던 감정들이 계속 맴돈다",
            "아직 에너지가 남아 있다",
            "현실 말고 다른 세계로 가고 싶다",
            "아무 생각 없이 웃고 싶다",
        ],
    ),
    (
        "큰 일정이 끝난 직후 가장 먼저 드는 생각은?",
        [
            "이제야 마음이 정리된다",
            "지금부터가 진짜 시작!",
            "한 단계 성장한 느낌",
            "웃긴 거부터 보고 싶다",
        ],
    ),
    (
        "영화관에 간다면 더 끌리는 건?",
        [
            "현실적이고 공감 가는 이야기",
            "속도감 있는 전개",
            "상상력을 자극하는 세계관",
            "편하게 웃을 수 있는 영화",
        ],
    ),
    (
        "친구가 영화를 보자고 하면?",
        [
            "여운 남는 영화면 좋겠어",
            "재밌고 시원한 거!",
            "현실 잊게 해주는 영화",
            "가볍게 웃을 수 있는 영화",
        ],
    ),
    (
        "영화를 보고 나서 가장 오래 남는 건?",
        [
            "감정과 메시지",
            "장면의 임팩트",
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
st.caption("질문에 답하면 취향에 맞는 영화만 골라드려요 🍿")

st.markdown("<br>", unsafe_allow_html=True)

# ----------------------
# 질문 진행
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
    with st.spinner("취향 분석 중... 🎬"):
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

    counts = Counter(st.session_state.answers.values())
    top_idx = counts.most_common(1)[0][0]
    selected_genre = genre_by_choice[top_idx]
    genre_id = genre_id_map[selected_genre]

    st.markdown(f"## 🎯 당신에게 딱인 장르는 **{selected_genre}**!")

    # 국가 파라미터 적용
    extra_params = country_params[country_option]

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

    for k, v in extra_params.items():
        discover_url += f"&{k}={v}"

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
