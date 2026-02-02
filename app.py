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
# CSS (UI 개선)
# ======================
st.markdown(
    """
    <style>
    .question-box {
        background-color: #f8f9fa;
        padding: 40px;
        border-radius: 20px;
        margin: 40px auto;
        max-width: 700px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    .question-title {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 20px;
    }
    .progress {
        font-size: 16px;
        color: #666;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
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
    st.session_state.step = 0

if "answers" not in st.session_state:
    st.session_state.answers = {}

# ======================
# 장르 매핑
# ======================
choice_to_genre = {
    # Q1
    "이불 덮고 감정 과몰입 영화 보기": "드라마",
    "친구랑 밤새 놀 각": "액션",
    "현실 탈출, 다른 세계로 도망": "판타지",
    "아무 생각 없이 웃긴 거 보기": "코미디",

    # Q2
    "허무한데 뭔가 뭉클함": "드라마",
    "지금 당장 날아갈 수 있음": "액션",
    "새로운 인생 챕터 시작 느낌": "SF",
    "밈 보면서 현실 도피": "코미디",

    # Q3
    "사진 찍기 좋은 감성 여행": "로맨스",
    "액티비티 풀코스 여행": "액션",
    "이 세계 아닌 느낌의 장소": "판타지",
    "사고 치고 웃고 오는 여행": "코미디",

    # Q4
    "인생이란 무엇인가…": "드라마",
    "다음 목표 뭐로 하지": "액션",
    "미래 세상 상상 중": "SF",
    "아무 생각 없음 ㅋㅋ": "코미디",

    # Q5
    "여운 남는 이야기": "드라마",
    "시원한 액션 쾌감": "액션",
    "세계관 미쳤는지": "SF",
    "웃기면 장땡": "코미디",
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
    "액션": "당신은 지루한 거 못 참는 타입 🔥",
    "코미디": "웃음이 인생의 큰 비중을 차지함 😂",
    "드라마": "감정 몰입 잘하는 섬세한 스타일 🎭",
    "SF": "상상력 풀가동 타입 🚀",
    "로맨스": "감정선과 관계에 약한 타입 💖",
    "판타지": "현실 탈출이 필요한 타입 ✨",
}

# ======================
# 질문 데이터 (재미 버전)
# ======================
questions = [
    ("강의 끝나고 집에 왔다. 지금 제일 하고 싶은 건?",
     [
         "이불 덮고 감정 과몰입 영화 보기",
         "친구랑 밤새 놀 각",
         "현실 탈출, 다른 세계로 도망",
         "아무 생각 없이 웃긴 거 보기",
     ]),
    ("시험 끝난 직후 상태는?",
     [
         "허무한데 뭔가 뭉클함",
         "지금 당장 날아갈 수 있음",
         "새로운 인생 챕터 시작 느낌",
         "밈 보면서 현실 도피",
     ]),
    ("여행 간다면 이건 꼭이다",
     [
         "사진 찍기 좋은 감성 여행",
         "액티비티 풀코스 여행",
         "이 세계 아닌 느낌의 장소",
         "사고 치고 웃고 오는 여행",
     ]),
    ("요즘 머릿속에 제일 많은 생각은?",
     [
         "인생이란 무엇인가…",
         "다음 목표 뭐로 하지",
         "미래 세상 상상 중",
         "아무 생각 없음 ㅋㅋ",
     ]),
    ("영화 볼 때 제일 중요함",
     [
         "여운 남는 이야기",
         "시원한 액션 쾌감",
         "세계관 미쳤는지",
         "웃기면 장땡",
     ]),
]

# ======================
# 제목
# ======================
st.title("🎬 나와 어울리는 영화는?")
st.caption("가볍게 답하고, 딱 맞는 영화 추천받기 🍿")

# ======================
# 질문 화면
# ======================
if st.session_state.step < len(questions):
    q, opts = questions[st.session_state.step]

    st.markdown(
        f"""
        <div class="question-box">
            <div class="progress">질문 {st.session_state.step + 1} / {len(questions)}</div>
            <div class="question-title">{q}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    answer = st.radio("", opts, index=None)

    if answer and st.button("다음 ➡️"):
        st.session_state.answers[st.session_state.step] = answer
        st.session_state.step += 1
        st.rerun()

# ======================
# 로딩
# ======================
elif st.session_state.step == len(questions):
    with st.spinner("🎥 취향 분석 중..."):
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

        st.markdown(f"## 🎯 당신에게 딱인 장르는 **{final_genre}**!")
        st.write(genre_reason[final_genre])

        url = (
            f"https://api.themoviedb.org/3/discover/movie"
            f"?api_key={api_key}"
            f"&with_genres={genre_id_map[final_genre]}"
            f"&language=ko-KR"
            f"&sort_by=vote_average.desc"
            f"&vote_count.gte=500"
        )

        movies = [
            m for m in requests.get(url).json().get("results", [])
            if m.get("poster_path")
        ][:6]

        st.markdown("### 🍿 추천 영화")

        cols = st.columns(3)
        for i, movie in enumerate(movies):
            with cols[i % 3]:
                st.image(
                    "https://image.tmdb.org/t/p/w342" + movie["poster_path"],
                    use_container_width=True,
                )
                st.markdown(f"**{movie['title']}**")
                st.caption(f"⭐ {movie['vote_average']}")

                with st.expander("줄거리"):
                    st.write(movie["overview"] or "줄거리 정보가 없습니다.")

        if st.button("🔄 다시 테스트하기"):
            st.session_state.clear()
            st.rerun()
