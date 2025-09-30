import os
import pickle
import streamlit as st
import requests
from passlib.hash import bcrypt
import time
from requests.exceptions import RequestException, ConnectionError

# --- Set Streamlit Page Config ---
st.set_page_config(page_title="Movie Recommender", layout="wide")

# --- File Paths ---
USER_DB = 'artifacts/users.pkl'
REVIEW_FILE = 'artifacts/reviews.pkl'

# --- Load or Create User Database ---
if os.path.exists(USER_DB):
    with open(USER_DB, 'rb') as f:
        users = pickle.load(f)
else:
    users = {}

# --- Save Users to File ---
def save_users():
    with open(USER_DB, 'wb') as f:
        pickle.dump(users, f)

# --- Load Reviews ---
if os.path.exists(REVIEW_FILE):
    with open(REVIEW_FILE, 'rb') as f:
        user_reviews = pickle.load(f)
else:
    user_reviews = {}

# --- TMDB API ---
def fetch_movie_details(movie_id):
    api_key = "5663e47e088e93119a28c7c0eff50434"  # Replace with your valid API key
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}&language=en-US"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (RequestException, ConnectionError) as e:
        print(f"Error fetching movie {movie_id}: {e}")
        return {
            'poster': "https://via.placeholder.com/500x750?text=No+Image",
            'overview': 'No description available.',
            'release_date': 'N/A',
            'genres': [],
            'rating': 'N/A',
            'title': 'Unavailable'
        }

    poster_path = data.get('poster_path')
    poster_url = "http://image.tmdb.org/t/p/w500" + poster_path if poster_path else "https://via.placeholder.com/500x750?text=No+Image"
    overview = data.get('overview', 'No description available.')
    release_date = data.get('release_date', 'N/A')
    genres = [genre['name'] for genre in data.get('genres', [])]
    rating = data.get('vote_average', 'N/A')

    return {
        'poster': poster_url,
        'overview': overview,
        'release_date': release_date,
        'genres': genres,
        'rating': rating,
        'title': data.get('title', 'Unavailable')
    }

# --- Recommend Similar Movies ---
def recommend(movie):
    index = movies[movies['title'] == movie].index[0]
    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    
    recommendations = []
    for i in distances[1:6]:  # Top 5 recommendations
        movie_id = movies.iloc[i[0]].movie_id
        time.sleep(1)  # Delay to avoid API rate limiting
        details = fetch_movie_details(movie_id)
        details['title'] = movies.iloc[i[0]].title
        recommendations.append(details)

    return recommendations

# --- Load Movie Data ---
movies = pickle.load(open('artifacts/movie_list.pkl', 'rb'))
similarity = pickle.load(open('artifacts/similarity.pkl', 'rb'))

# --- Session State ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'show_recommendations' not in st.session_state:
    st.session_state.show_recommendations = False
if 'page' not in st.session_state:
    st.session_state.page = "Login"

# --- Register New User ---
def register():
    st.subheader("📝 Register")
    new_user = st.text_input("Choose a username")
    new_pass = st.text_input("Choose a password", type="password")
    if st.button("Register"):
        if new_user in users:
            st.warning("⚠ Username already exists.")
        else:
            hashed_pw = bcrypt.hash(new_pass)
            users[new_user] = hashed_pw
            save_users()
            st.success("✅ Registration successful! Please login.")
            st.session_state.page = "Login"

# --- Login Page ---
def login():
    st.subheader("🔐 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in users and bcrypt.verify(password, users[username]):
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"Welcome, {username}!")
            st.rerun()
        else:
            st.error("❌ Invalid credentials")

# --- Main Movie App ---
def movie_app():
    st.header("🎬 Movie Recommendation System Using Machine Learning")

    st.markdown(f"👤 Logged in as: *{st.session_state.username}*")
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    movie_list = movies['title'].values
    selected_movie = st.selectbox('🎥 Select a movie to get recommendations', movie_list)

    if st.button('🎯 Show recommendation'):
        st.session_state.selected_movie = selected_movie
        st.session_state.show_recommendations = True

    if st.session_state.get('show_recommendations', False):
        selected_movie = st.session_state.selected_movie
        recommendations = recommend(selected_movie)

        st.subheader("📽 Recommended Movies")
        cols = st.columns(5)
        for i, movie in enumerate(recommendations):
            with cols[i]:
                st.image(movie['poster'])
                st.markdown(f"**{movie['title']}**")
                st.markdown(f"🎬 *Genres:* {', '.join(movie['genres'])}")
                st.markdown(f"📅 *Release:* {movie['release_date'][:4]}")
                st.markdown(f"⭐ *Rating:* {movie['rating']}")
                st.markdown(f"📝 *Overview:* {movie['overview'][:150]}...")

        # User rating and reviews
        st.markdown("---")
        st.subheader(f"⭐ Rate and Review: {selected_movie}")
        user_rating = st.slider("Your Rating (1 to 5)", 1, 5, 3)
        user_review = st.text_area("✍ Write your review")

        if st.button("Submit Review"):
            if user_review.strip():
                if selected_movie not in user_reviews:
                    user_reviews[selected_movie] = {'ratings': [], 'reviews': []}
                user_reviews[selected_movie]['ratings'].append(user_rating)
                user_reviews[selected_movie]['reviews'].append(f"{st.session_state.username}: {user_review.strip()}")
                with open(REVIEW_FILE, 'wb') as f:
                    pickle.dump(user_reviews, f)
                st.success("✅ Review submitted!")
            else:
                st.warning("⚠ Please write a review before submitting.")

        if selected_movie in user_reviews:
            st.subheader("🗣 User Feedback")
            ratings = user_reviews[selected_movie]['ratings']
            reviews = user_reviews[selected_movie]['reviews']
            if ratings:
                avg_rating = sum(ratings) / len(ratings)
                st.write(f"📊 Average Rating: {avg_rating:.1f}/5 from {len(ratings)} users")
            for i, review in enumerate(reviews):
                st.markdown(f"*Review {i+1}:* {review}")
        else:
            st.info("No reviews yet. Be the first to leave one!")

    st.markdown("---")
    st.subheader("🏆 Top Rated Movies")
    if user_reviews:
        avg_ratings = {
            movie: sum(data['ratings']) / len(data['ratings'])
            for movie, data in user_reviews.items() if data['ratings']
        }
        top_movies = sorted(avg_ratings.items(), key=lambda x: x[1], reverse=True)[:5]
        for title, rating in top_movies:
            st.markdown(f"⭐ *{title}* — {rating:.1f}/5")

# --- Navigation ---
st.sidebar.title("Navigation")
st.session_state.page = st.sidebar.radio(
    "Go to", 
    ["Login", "Register", "App"] if not st.session_state.logged_in else ["App"]
)

if st.session_state.page == "Login" and not st.session_state.logged_in:
    login()
elif st.session_state.page == "Register":
    register()
elif st.session_state.logged_in:
    movie_app()
else:
    login()
