# App Review Viewer

A tool to periodically collect iOS App Store and Google Play Store reviews, store them in Google Cloud Storage, and view them via a web interface.

## Features
- **Periodic Collection**: Automatically fetches new reviews via GitHub Actions.
- **Efficient Storage**: Stores data in partitioned JSON files on GCS to handle large datasets.
- **Smart Indexing**: Keeps an index of versions and dates for fast querying.
- **Web Interface**:
  - Filter by Date, Version, Country, and Rating.
  - Keyword Search.
  - "Google-like" Material Design UI.

## Setup

### Prerequisites
- Python 3.9+
- A Google Cloud Platform project (for GCS)

### Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Configuration
Edit `config.yaml` to specify the apps you want to track.

### Running Locally

**1. Collect Reviews (Local Mode)**
This will fetch reviews and save them to `data_local/` folder instead of GCS.
```bash
python src/collector/main.py --local
```

**2. Start Web App**
```bash
streamlit run src/web/app.py
```

### Running with GCS
See [docs/GCS_SETUP.md](docs/GCS_SETUP.md) for instructions on setting up Google Cloud Storage and GitHub Actions.
