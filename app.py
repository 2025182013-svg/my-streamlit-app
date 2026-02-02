import streamlit as st
import requests
from collections import Counter
import time

st.set_page_config(
    page_title="나와 어울리는 영화는?",
    page_icon="🎬",
    layout="wide",
)

# ----------------------
# TMDB API 설정
# ----------------------
st.sidebar.title("🔑 TMDB 설정")
api_key = st.sidebar.text_input("TMDB API 키 입력", type="password")
language = "ko-KR"

if not api_key:
    st.sidebar.warning("⚠️ API 키가 필요해요!")

# ----------------------
# Session State
# ----------------------
if "step" not in st.session_state:
    st.session_state.step = 0
if "answers" not in st.session_state:
    st.session_state.answers = {}

# ----------------------
# 질문 목록
# ----------------------
questions = [
    ("집에 왔을 때 기분은?", ["감정 과몰입", "노는 게 최고", "다른 세계로", "아무거나 웃긴거"]),
    ("시험 끝난 직후 느낌은?", ["허무/감성", "날아갈 듯", "새 시작", "밈 타임"]),
    ("여행 스타일은?", ["감성 사진 여행", "액티비티 풀코스", "판타지 느낌 장소", "웃음 폭발 여행"]),
    ("현재 생각 주제는?", ["인생 뭐지", "다음 목표", "미래 상상", "아무 생각 없음"]),
    ("영화에서 가장 중요한 요소?", ["여운 있는 이야기", "시원한 액션", "세계관", "순수 코미디"]),
]

genre_map = {
    0: "드라마", 1: "액션", 2: "판타지", 3: "코미디",
    4: "SF",   5: "로맨스"
}

genre_id_map = {
    "액션": 28, "코미디": 35, "드라마": 18,
    "SF": 878, "로맨스": 10749, "판타지": 14,
}

# ----------------------
# 질문 진행
# ----------------------
st.title("🎬 영화 추천 심리테스트")

if st.session_state.step < len(questions):
    q_text, opts = questions[st.session_state.step]
    st.markdown(f"### Q{st.session_state.step + 1}: {q_text}")
    answer = st.radio("", opts, key=f"q{st.session_state.step}")

    if answer and st.button("다음"):
        st.session_state.answers[st.session_state.step] = answer
        st.session_state.step += 1
        st.rerun()

elif st.session_state.step == len(questions):
    with st.spinner("분석 중... 🍿"):
        time.sleep(1)
        st.session_state.step += 1
        st.rerun()

else:
    st.header("🔍 분석 결과")

    if not api_key:
        st.error("API 키가 필요합니다!")
    else:
        # 장르 결정
        answers = list(st.session_state.answers.values())
        genre_counts = Counter(answers)
        top_choice = genre_counts.most_common(1)[0][0]
        selected_genre = top_choice

        if selected_genre not in genre_id_map:
            selected_genre = "드라마"

        genre_id = genre_id_map[selected_genre]

        st.write(f"🎯 **{selected_genre} 장르 추천!**")

        # Discover API - 인기 + 평점 높은순
        url_disc = (
            f"https://api.themoviedb.org/3/discover/movie"
            f"?api_key={api_key}"
            f"&language={language}"
            f"&with_genres={genre_id}"
            f"&sort_by=vote_average.desc"
            f"&vote_count.gte=300"
        )
        res_disc = requests.get(url_disc).json().get("results", [])

        # 정렬: 평점 높은 순
        movies = sorted(res_disc, key=lambda x: x.get("vote_average", 0), reverse=True)[:6]

        st.markdown("## 🍿 추천 영화 TOP 6")

        cols = st.columns(3)
        for i, movie in enumerate(movies):
            with cols[i % 3]:
                poster = movie.get("poster_path")
                if poster:
                    st.image(f"https://image.tmdb.org/t/p/w342{poster}", use_container_width=True)
                st.markdown(f"**{movie['title']}**")
                st.write(f"⭐ {movie['vote_average']} / 💬 {movie['vote_count']}")

                with st.expander("줄거리"):
                    st.write(movie.get("overview", "정보 없음"))

        st.markdown("---")
        if st.button("🔄 다시 하기"):
            st.session_state.clear()
            st.rerun()
