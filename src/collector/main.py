import yaml
import os
import argparse
from dotenv import load_dotenv
from fetcher import fetch_ios_reviews, fetch_android_reviews
from storage import StorageManager

# Load environment variables from .env file if present
load_dotenv()

def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--local', action='store_true', help='Run locally without GCS')
    args = parser.parse_args()

    config = load_config()

    # Environment variable overrides config if present
    bucket_name = os.environ.get('GCS_BUCKET_NAME', config['storage']['bucket_name'])

    storage = StorageManager(bucket_name, local_run=args.local)
    base_path = config['storage']['base_path']

    all_reviews = []

    for app in config['apps']:
        print(f"Processing App: {app['name']}")
        for country in app['countries']:
            print(f"  Fetching for country: {country}")

            # iOS
            if 'ios_id' in app:
                print(f"    Fetching iOS...")
                ios_reviews = fetch_ios_reviews(app['ios_id'], country)
                print(f"      Got {len(ios_reviews)} reviews.")
                all_reviews.extend(ios_reviews)

            # Android
            if 'android_id' in app:
                print(f"    Fetching Android...")
                android_reviews = fetch_android_reviews(app['android_id'], country)
                print(f"      Got {len(android_reviews)} reviews.")
                all_reviews.extend(android_reviews)

    if all_reviews:
        print(f"Saving {len(all_reviews)} reviews total...")
        storage.save_reviews(all_reviews, base_path=base_path)
    else:
        print("No reviews fetched.")

if __name__ == "__main__":
    main()
