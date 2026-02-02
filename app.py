import streamlit as st
import requests

# =============================
# 기본 설정
# =============================
st.set_page_config(page_title="🎬 영화 추천 통합 앱", layout="wide")

TMDB_BASE = "https://api.themoviedb.org/3"
POSTER_BASE = "https://image.tmdb.org/t/p/w342"

# =============================
# 장르 설정
# =============================
GENRE_IDS = {
    "액션": 28,
    "코미디": 35,
    "SF": 878,
    "드라마": 18,
    "로맨스": 10749,
    "판타지": 14
}

GENRE_MOOD_KEYWORDS = {
    "액션": "action adventure energy",
    "로맨스": "romantic sunset love",
    "SF": "space galaxy stars",
    "코미디": "happy fun colorful",
    "드라마": "emotional rain cinematic",
    "판타지": "fantasy magical forest"
}

# =============================
# 사이드바
# =============================
st.sidebar.header("🔑 API 키 입력")

tmdb_key = st.sidebar.text_input("TMDB API Key", type="password")
unsplash_key = st.sidebar.text_input("Unsplash Access Key", type="password")

st.sidebar.divider()
genre = st.sidebar.selectbox("🎭 오늘의 장르", list(GENRE_IDS.keys()))

# =============================
# Unsplash 분위기 이미지
# =============================
def get_mood_image(genre, access_key):
    query = GENRE_MOOD_KEYWORDS.get(genre, "movie cinema mood")

    url = "https://api.unsplash.com/search/photos"
    params = {
        "query": query,
        "client_id": access_key,
        "per_page": 1,
        "orientation": "landscape"
    }

    try:
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        if data.get("results"):
            return data["results"][0]["urls"]["regular"]
    except Exception:
        pass

    return None

# =============================
# 통합 결과 함수
# =============================
def get_complete_result(genre, tmdb_key, unsplash_key):
    result = {}

    # 1️⃣ TMDB 영화 3편
    tmdb_url = f"{TMDB_BASE}/discover/movie"
    tmdb_params = {
        "api_key": tmdb_key,
        "language": "ko-KR",
        "with_genres": GENRE_IDS[genre],
        "sort_by": "popularity.desc"
    }
    tmdb_res = requests.get(tmdb_url, params=tmdb_params)
    result["movies"] = tmdb_res.json().get("results", [])[:3]

    # 2️⃣ Unsplash 분위기 이미지
    result["mood_image"] = get_mood_image(genre, unsplash_key)

    # 3️⃣ ZenQuotes 명언
    quote_res = requests.get("https://zenquotes.io/api/random")
    quote_data = quote_res.json()
    result["quote"] = {
        "content": quote_data[0]["q"],
        "author": quote_data[0]["a"]
    }

    return result

# =============================
# 메인 UI
# =============================
st.title("🎬 오늘의 장르별 영화 추천")

st.caption("TMDB · Unsplash · ZenQuotes API를 하나로 결합한 추천 앱")

if st.button("🎯 결과 보기"):
    if not tmdb_key or not unsplash_key:
        st.error("사이드바에 모든 API 키를 입력해주세요.")
        st.stop()

    with st.spinner("여러 API에서 데이터를 불러오는 중..."):
        result = get_complete_result(genre, tmdb_key, unsplash_key)

    # -------------------------
    # 1️⃣ 상단: 장르 결과
    # -------------------------
    st.header(f"🎭 오늘의 장르: {genre}")

    # -------------------------
    # 2️⃣ 중간: 영화 카드 3개
    # -------------------------
    st.subheader("🍿 추천 영화")

    cols = st.columns(3)
    for col, movie in zip(cols, result["movies"]):
        with col:
            if movie.get("poster_path"):
                st.image(POSTER_BASE + movie["poster_path"])
            st.markdown(f"**{movie['title']}**")
            st.write("⭐ 평점:", movie["vote_average"])

    # -------------------------
    # 3️⃣ 하단: 분위기 이미지 + 명언
    # -------------------------
    st.subheader("🎨 오늘의 분위기")

    if result["mood_image"]:
        st.image(result["mood_image"], use_container_width=True)

    quote = result["quote"]
    st.markdown(
        f"""
        > *{quote['content']}*  
        > — **{quote['author']}**
        """
    )
