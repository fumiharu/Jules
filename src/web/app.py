import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from google.cloud import storage
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

# --- Configuration & Setup ---
st.set_page_config(
    page_title="App Review Viewer",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for "Google-like" feel
st.markdown("""
<style>
    .review-card {
        background-color: white;
        padding: 20px;
        border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
        margin-bottom: 20px;
        border: 1px solid #e0e0e0;
    }
    .review-header {
        display: flex;
        justify_content: space-between;
        align_items: center;
        margin-bottom: 10px;
    }
    .review-author {
        font-weight: bold;
        color: #202124;
    }
    .review-date {
        color: #5f6368;
        font-size: 0.9em;
    }
    .review-rating {
        color: #fa7b17; /* Star color */
    }
    .review-content {
        color: #202124;
        line-height: 1.5;
    }
    .review-meta {
        margin-top: 10px;
        font-size: 0.8em;
        color: #5f6368;
    }
    .stApp {
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

# --- Data Loading ---

@st.cache_resource
def get_storage_client():
    # If running locally without auth env vars, this might fail unless using a key file.
    # We assume the user sets up GOOGLE_APPLICATION_CREDENTIALS or runs locally in 'local mode'.
    try:
        return storage.Client()
    except:
        return None

BUCKET_NAME = os.environ.get('GCS_BUCKET_NAME', 'YOUR_GCS_BUCKET_NAME')
BASE_PATH = "reviews"
LOCAL_DATA_DIR = "data_local" # For local testing fallback

def load_json(path, client=None):
    """Loads JSON from GCS or local fallback."""
    if client and BUCKET_NAME != 'YOUR_GCS_BUCKET_NAME':
        try:
            bucket = client.bucket(BUCKET_NAME)
            blob = bucket.blob(path)
            if blob.exists():
                return json.loads(blob.download_as_string())
        except Exception as e:
            st.warning(f"Failed to load from GCS: {e}")
            pass

    # Fallback to local
    local_path = os.path.join(LOCAL_DATA_DIR, path)
    if os.path.exists(local_path):
        with open(local_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

@st.cache_data(ttl=3600)
def load_index():
    path = f"{BASE_PATH}/index.json"
    client = get_storage_client()
    data = load_json(path, client)
    if not data:
        return {"versions": {}}
    return data

@st.cache_data(ttl=600)
def load_reviews_data(files_to_load):
    """
    Loads multiple JSON files and combines them.
    files_to_load: List of paths relative to bucket root (e.g. reviews/jp/2024/05.json)
    """
    client = get_storage_client()
    all_reviews = []

    for path in files_to_load:
        data = load_json(path, client)
        if data:
            all_reviews.extend(data)

    return all_reviews

# --- Main App Logic ---

def main():
    st.title("📱 App Review Viewer")

    # 1. Load Index
    index_data = load_index()
    versions_map = index_data.get("versions", {})

    # Calculate available countries and versions from index
    available_versions = sorted(versions_map.keys(), reverse=True)
    available_countries = set()
    for v_data in versions_map.values():
        available_countries.update(v_data.keys())
    available_countries = sorted(list(available_countries))
    if not available_countries:
        available_countries = ['jp'] # Default fallback

    # --- Sidebar Filters ---
    st.sidebar.header("Filters")

    # Country Filter
    selected_country = st.sidebar.selectbox("Country", available_countries, index=0)

    # Version Filter (Optional)
    use_version_filter = st.sidebar.checkbox("Filter by Version")
    selected_version = None
    if use_version_filter:
        selected_version = st.sidebar.selectbox("Version", available_versions)

    # Date Range Filter
    # Default: Last 30 days or based on loaded data.
    # Since we lazy load, we need a strategy.
    # Strategy:
    # If Version Filter is ON -> Load files from index for that version.
    # If Version Filter is OFF -> Load files for selected date range (default last 3 months).

    today = datetime.today()
    start_date = st.sidebar.date_input("Start Date", value=today.replace(month=today.month-1 if today.month > 1 else 12))
    end_date = st.sidebar.date_input("End Date", value=today)

    # Rating Filter
    selected_ratings = st.sidebar.multiselect("Rating", [1, 2, 3, 4, 5], default=[1, 2, 3, 4, 5])

    # Search
    search_query = st.sidebar.text_input("Keyword Search")

    # --- Determine Files to Load ---
    files_to_load = set()

    if use_version_filter and selected_version:
        # Load specific files for this version
        if selected_version in versions_map and selected_country in versions_map[selected_version]:
            ym_list = versions_map[selected_version][selected_country]
            for ym in ym_list:
                files_to_load.add(f"{BASE_PATH}/{selected_country}/{ym}.json")
        else:
            st.warning(f"No data found for Version {selected_version} in {selected_country}")
    else:
        # Load by Date Range (Month granularity)
        # Generate list of YYYY/MM between start and end date
        current = start_date.replace(day=1)
        while current <= end_date:
            ym = current.strftime('%Y/%m')
            path = f"{BASE_PATH}/{selected_country}/{ym}.json"
            files_to_load.add(path)

            # Increment month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

    # --- Load & Process Data ---
    if not files_to_load:
        st.info("No data files match the criteria.")
        return

    with st.spinner(f"Loading {len(files_to_load)} files..."):
        raw_reviews = load_reviews_data(list(files_to_load))

    if not raw_reviews:
        st.info("No reviews found in the selected files.")
        return

    df = pd.DataFrame(raw_reviews)

    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])

    # Apply Filters

    # 1. Country (Already loaded by country, but double check data integrity)
    df = df[df['country'] == selected_country]

    # 2. Date Range
    # (We loaded whole months, so we must filter by precise date now)
    df = df[(df['date'].dt.date >= start_date) & (df['date'].dt.date <= end_date)]

    # 3. Version
    if use_version_filter and selected_version:
        df = df[df['version'] == selected_version]

    # 4. Rating
    df = df[df['rating'].isin(selected_ratings)]

    # 5. Search
    if search_query:
        query = search_query.lower()
        df = df[
            df['content'].str.lower().str.contains(query, na=False) |
            df['title'].str.lower().str.contains(query, na=False)
        ]

    # --- Display ---
    st.subheader(f"Reviews ({len(df)})")

    # Sort by date desc
    df = df.sort_values(by='date', ascending=False)

    for _, row in df.iterrows():
        stars = "★" * int(row['rating']) + "☆" * (5 - int(row['rating']))

        st.markdown(f"""
        <div class="review-card">
            <div class="review-header">
                <span class="review-author">{row['user_name']}</span>
                <span class="review-date">{row['date'].strftime('%Y-%m-%d')}</span>
            </div>
            <div class="review-rating">{stars}</div>
            <div class="review-content">{row['content']}</div>
            <div class="review-meta">
                Version: {row['version']} | Source: {row['source']} | {row['country'].upper()}
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
