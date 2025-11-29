import json
import os
from google.cloud import storage
import datetime

class StorageManager:
    def __init__(self, bucket_name, local_run=False):
        self.bucket_name = bucket_name
        self.local_run = local_run
        if not local_run and bucket_name:
            self.client = storage.Client()
            self.bucket = self.client.bucket(bucket_name)
        else:
            self.client = None
            self.bucket = None
            # Ensure local directories exist
            os.makedirs("data_local", exist_ok=True)

    def _read_json(self, path):
        if self.local_run or not self.bucket:
            local_path = os.path.join("data_local", path)
            if os.path.exists(local_path):
                with open(local_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return None
        else:
            blob = self.bucket.blob(path)
            if blob.exists():
                return json.loads(blob.download_as_string())
            return None

    def _write_json(self, path, data):
        if self.local_run or not self.bucket:
            local_path = os.path.join("data_local", path)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
            print(f"Saved locally to {local_path}")
        else:
            blob = self.bucket.blob(path)
            blob.upload_from_string(
                json.dumps(data, ensure_ascii=False, default=str),
                content_type='application/json'
            )
            print(f"Uploaded to gs://{self.bucket_name}/{path}")

    def save_reviews(self, reviews, base_path="reviews"):
        """
        Saves reviews to partitioned files and updates the index.
        reviews: List of dicts (must have 'date', 'country', 'version')
        """
        # 1. Group by Country and Year-Month
        grouped = {}
        for r in reviews:
            dt = r['date']
            if isinstance(dt, str):
                dt = datetime.datetime.fromisoformat(dt)

            ym = dt.strftime('%Y/%m')
            country = r['country']
            key = (country, ym)

            if key not in grouped:
                grouped[key] = []
            grouped[key].append(r)

        # 2. Load existing data for these groups, merge, and save
        affected_files = [] # List of paths that were updated

        for (country, ym), new_reviews in grouped.items():
            path = f"{base_path}/{country}/{ym}.json"
            existing_reviews = self._read_json(path) or []

            # Merge logic: Deduplicate by ID
            existing_ids = {r['id'] for r in existing_reviews}
            merged = existing_reviews
            for nr in new_reviews:
                if nr['id'] not in existing_ids:
                    merged.append(nr)
                    existing_ids.add(nr['id'])

            # Sort by date desc
            merged.sort(key=lambda x: x['date'], reverse=True)

            self._write_json(path, merged)
            affected_files.append({
                'path': path,
                'country': country,
                'ym': ym,
                'reviews': merged
            })

        # 3. Update Index
        self.update_index(affected_files, base_path)

    def update_index(self, updated_files_info, base_path):
        """
        Updates the global index.json with version mappings.
        updated_files_info: list of dicts with keys 'path', 'country', 'ym', 'reviews'
        """
        index_path = f"{base_path}/index.json"
        index_data = self._read_json(index_path) or {"versions": {}, "updated_at": ""}

        # Structure of index.json:
        # {
        #   "updated_at": "...",
        #   "versions": {
        #       "13.4.0": {
        #           "jp": ["2024/05", "2024/06"],
        #           "us": ["2024/05"]
        #       }
        #   }
        # }

        if "versions" not in index_data:
            index_data["versions"] = {}

        for info in updated_files_info:
            country = info['country']
            ym = info['ym']
            # We need to scan the FULL content of this updated file to know which versions are in it.
            # (Because we might have added a new version to an existing month,
            #  or the file might already have had versions we need to preserve)

            # Extract all unique versions in this file
            versions_in_file = set()
            for r in info['reviews']:
                v = r.get('version')
                if not v:
                    v = "Unknown"
                versions_in_file.add(v)

            # Update the global map
            for v in versions_in_file:
                if v not in index_data["versions"]:
                    index_data["versions"][v] = {}

                if country not in index_data["versions"][v]:
                    index_data["versions"][v][country] = []

                # Add this YM if not present
                if ym not in index_data["versions"][v][country]:
                    index_data["versions"][v][country].append(ym)
                    # Keep sorted?
                    index_data["versions"][v][country].sort()

        index_data["updated_at"] = datetime.datetime.now().isoformat()
        self._write_json(index_path, index_data)
