import streamlit as st
import requests
from collections import Counter
import time

st.set_page_config(
    page_title="나와 어울리는 영화는?",
    page_icon="🎬",
    layout="wide",
)

# ======================
# Sidebar
# ======================
st.sidebar.title("🔑 TMDB API 설정")
api_key = st.sidebar.text_input("TMDB API Key", type="password")

# ======================
# Session State
# ======================
if "step" not in st.session_state:
    st.session_state.step = 0  # 질문 → 로딩 → 결과

if "answers" not in st.session_state:
    st.session_state.answers = {}

# ======================
# 장르 매핑
# ======================
choice_to_genre = {
    "감정선을 건드리는 영화 한 편 보며 혼자 여운에 잠긴다": "드라마",
    "몸이 좀 피곤해도 친구들이랑 액티비티나 게임을 즐긴다": "액션",
    "현실을 잠시 잊을 수 있는 세계관 속으로 빠져들고 싶다": "판타지",
    "아무 생각 없이 웃을 수 있는 콘텐츠를 틀어놓는다": "코미디",

    "“수고했다”는 말이 어울리는 잔잔한 감정": "드라마",
    "해방감 MAX! 지금 당장 뭐든 할 수 있을 것 같다": "액션",
    "이제 새로운 스테이지로 넘어간 느낌": "SF",
    "드디어 밈과 웃긴 영상 볼 시간이 생겼다": "코미디",

    "감성적인 카페와 풍경을 천천히 즐기는 여행": "로맨스",
    "액티비티 가득한 일정, 가만히 있는 건 못 참는다": "액션",
    "이국적이거나 비현실적인 분위기의 장소 탐방": "판타지",
    "계획은 대충, 웃긴 에피소드가 많이 생기는 여행": "코미디",

    "요즘 인간관계나 감정에 대해 생각이 많아": "드라마",
    "다음에 뭘 해볼지, 목표 같은 게 머릿속에 있다": "액션",
    "세상이나 미래, 가능성 같은 상상을 자주 한다": "SF",
    "솔직히 별생각 안 하고 살고 있음 ㅋㅋ": "코미디",

    "인물의 감정과 현실적인 이야기": "드라마",
    "긴장감 넘치는 전개와 시원한 장면": "액션",
    "독특한 세계관과 상상력을 자극하는 설정": "SF",
    "웃음 포인트와 가볍게 즐길 수 있는 분위기": "코미디",
}

genre_id_map = {
    "액션": 28,
    "코미디": 35,
    "드라마": 18,
    "SF": 878,
    "로맨스": 10749,
    "판타지": 14,
}

genre_reason = {
    "액션": "에너지 넘치고 몰입감 강한 전개를 좋아하는 당신!",
    "코미디": "웃음이 최고인 힐링형 영화 취향이에요.",
    "드라마": "감정선과 이야기에 깊이 공감하는 타입이에요.",
    "SF": "상상력과 새로운 세계관에 끌리는 당신!",
    "로맨스": "감정과 관계의 흐름을 중요하게 여겨요.",
    "판타지": "현실을 벗어난 세계에서 즐거움을 찾는 타입이에요.",
}

# ======================
# 질문 데이터
# ======================
questions = [
    (
        "하루 종일 강의가 끝난 후, 저녁에 가장 하고 싶은 것은?",
        [
            "감정선을 건드리는 영화 한 편 보며 혼자 여운에 잠긴다",
            "몸이 좀 피곤해도 친구들이랑 액티비티나 게임을 즐긴다",
            "현실을 잠시 잊을 수 있는 세계관 속으로 빠져들고 싶다",
            "아무 생각 없이 웃을 수 있는 콘텐츠를 틀어놓는다",
        ],
    ),
    (
        "시험이 끝난 직후, 당신의 기분과 가장 가까운 상태는?",
        [
            "“수고했다”는 말이 어울리는 잔잔한 감정",
            "해방감 MAX! 지금 당장 뭐든 할 수 있을 것 같다",
            "이제 새로운 스테이지로 넘어간 느낌",
            "드디어 밈과 웃긴 영상 볼 시간이 생겼다",
        ],
    ),
    (
        "여행을 간다면 가장 끌리는 여행 스타일은?",
        [
            "감성적인 카페와 풍경을 천천히 즐기는 여행",
            "액티비티 가득한 일정, 가만히 있는 건 못 참는다",
            "이국적이거나 비현실적인 분위기의 장소 탐방",
            "계획은 대충, 웃긴 에피소드가 많이 생기는 여행",
        ],
    ),
    (
        "친구가 “너 요즘 무슨 생각해?”라고 물어본다면?",
        [
            "요즘 인간관계나 감정에 대해 생각이 많아",
            "다음에 뭘 해볼지, 목표 같은 게 머릿속에 있다",
            "세상이나 미래, 가능성 같은 상상을 자주 한다",
            "솔직히 별생각 안 하고 살고 있음 ㅋㅋ",
        ],
    ),
    (
        "당신이 영화에서 가장 중요하게 여기는 요소는?",
        [
            "인물의 감정과 현실적인 이야기",
            "긴장감 넘치는 전개와 시원한 장면",
            "독특한 세계관과 상상력을 자극하는 설정",
            "웃음 포인트와 가볍게 즐길 수 있는 분위기",
        ],
    ),
]

# ======================
# 제목
# ======================
st.title("🎬 나와 어울리는 영화는?")
st.caption("질문에 답하면, 당신에게 딱 맞는 영화를 추천해드려요 🍿")
st.divider()

# ======================
# 질문 화면
# ======================
if st.session_state.step < len(questions):
    q, opts = questions[st.session_state.step]
    st.markdown(f"### Q{st.session_state.step + 1}")
    answer = st.radio(q, opts, index=None)

    if answer and st.button("다음 ➡️"):
        st.session_state.answers[st.session_state.step] = answer
        st.session_state.step += 1
        st.rerun()

# ======================
# 로딩
# ======================
elif st.session_state.step == len(questions):
    with st.spinner("🎥 당신에게 어울리는 영화를 찾고 있어요..."):
        time.sleep(2)
        st.session_state.step += 1
        st.rerun()

# ======================
# 결과
# ======================
else:
    if not api_key:
        st.warning("TMDB API Key를 입력해 주세요.")
    else:
        genres = [choice_to_genre[a] for a in st.session_state.answers.values()]
        final_genre = Counter(genres).most_common(1)[0][0]
        genre_id = genre_id_map[final_genre]

        st.markdown(f"## 🎯 당신에게 딱인 장르는 **{final_genre}**!")
        st.write(genre_reason[final_genre])

        url = (
            f"https://api.themoviedb.org/3/discover/movie"
            f"?api_key={api_key}"
            f"&with_genres={genre_id}"
            f"&language=ko-KR"
            f"&sort_by=popularity.desc"
            f"&vote_count.gte=100"
        )

        response = requests.get(url)

        if response.status_code != 200:
            st.error("영화 정보를 불러오지 못했어요 😢")
        else:
            movies = [
                m for m in response.json().get("results", [])
                if m.get("poster_path")
            ][:6]

            if not movies:
                st.warning("추천할 영화가 없어요 😢")
            else:
                st.markdown("### 🍿 추천 영화")

                cols = st.columns(3)
                for i, movie in enumerate(movies):
                    with cols[i % 3]:
                        st.image(
                            "https://image.tmdb.org/t/p/w500" + movie["poster_path"],
                            use_container_width=True,
                        )
                        st.markdown(f"**{movie['title']}**")
                        st.write(f"⭐ {movie['vote_average']}")

                        with st.expander("자세히 보기"):
                            st.write(movie["overview"] or "줄거리 정보가 없습니다.")
                            st.caption(
                                f"이 영화는 당신의 **{final_genre}** 취향과 잘 어울려요 💖"
                            )

        st.divider()
        if st.button("🔄 다시 테스트하기"):
            st.session_state.clear()
            st.rerun()
