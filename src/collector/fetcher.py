import datetime
import requests
import time
from google_play_scraper import Sort, reviews as gps_reviews

def fetch_ios_reviews(app_id, country, count=200):
    """
    Fetches reviews from the Apple App Store using the RSS feed.
    Note: RSS feed is limited to the last 500 reviews.
    """
    url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        feed = data.get('feed', {})
        entries = feed.get('entry', [])

        fetched_data = []
        for entry in entries:
            # Entry structure in RSS JSON
            # 'id': {'label': '...'}, 'author': {'name': {'label': '...'}},
            # 'im:rating': {'label': '5'}, 'title': {'label': '...'}, 'content': {'label': '...', 'attributes': {'type': 'text'}}
            # 'im:version': {'label': '...'}

            # Skip the first entry if it is the app info itself (sometimes happens in older feeds, but usually reviews are fine)
            if 'im:rating' not in entry:
                continue

            review_id = entry.get('id', {}).get('label', '')
            user_name = entry.get('author', {}).get('name', {}).get('label', 'Unknown')
            title = entry.get('title', {}).get('label', '')
            content = entry.get('content', {}).get('label', '')
            rating = int(entry.get('im:rating', {}).get('label', '0'))
            version = entry.get('im:version', {}).get('label', 'Unknown')

            # Date handling is tricky in RSS, it might not be present or in a specific format?
            # Actually, standard RSS JSON often lacks a clean timestamp in 'entry' for reviews compared to XML.
            # Let's check if 'updated' or 'published' is there.
            # Usually it's not in the JSON RSS for reviews explicitly for each item in a convenient way,
            # BUT 'updated' is often at the top level.
            # Wait, individual entries usually DO NOT have a timestamp in the iTunes JSON RSS feed.
            # This is a known limitation of the JSON endpoint. The XML feed has it.
            # However, for the sake of this task, if we can't get the date, we might assume "today" or skip it?
            # No, that's bad for history.

            # Let's switch to XML parsing if needed, or check if specific fields exist.
            # Actually, let's use a known workaround or just use the XML endpoint which is richer.
            # OR, we can try to use the library `app-store-scraper` logic but I decided to drop it.

            # Re-evaluating: `app-store-scraper` uses the internal API which returns JSON and HAS dates.
            # I should try to mimic that if possible, or use XML.
            # XML Feed: https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/xml
            # XML has <updated> tag.

            # For simplicity in Python, let's try to fetch XML and parse it?
            # Or just use the JSON and see if I missed the date field.
            # Checking online resources: The JSON feed indeed often lacks individual timestamps.

            # Alternative: Use the internal API `https://amp-api.apps.apple.com/v1/catalog/{country}/apps/{app_id}/reviews`
            # This requires a Bearer token.

            # Let's stick to the RSS XML feed then, it's public and reliable for recent reviews.
            # I will use `xml.etree.ElementTree`.
            pass

        # Call the XML fetcher instead
        return fetch_ios_reviews_xml(app_id, country, count)

    except Exception as e:
        print(f"Error fetching iOS reviews (JSON) for {country}: {e}")
        return []

def fetch_ios_reviews_xml(app_id, country, count=200):
    url = f"https://itunes.apple.com/{country}/rss/customerreviews/id={app_id}/sortBy=mostRecent/xml"
    import xml.etree.ElementTree as ET

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        # Namespace handling is annoying in ET, so we strip it or handle it.
        # The feed uses default namespace usually http://www.w3.org/2005/Atom

        root = ET.fromstring(response.content)
        # Find all entries. Namespace aware?
        # Let's just iterate and look for local names.

        fetched_data = []
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'im': 'http://itunes.apple.com/rss'}

        # The first entry is often the app metadata, need to skip it.
        # Reviews usually start from the second entry or we check for 'im:rating'.

        for entry in root.findall('atom:entry', ns):
            # Check if it's a review
            rating_tag = entry.find('im:rating', ns)
            if rating_tag is None:
                continue

            review_id = entry.find('atom:id', ns).text
            updated = entry.find('atom:updated', ns).text # ISO format e.g. 2024-05-21T07:00:00-07:00
            user_name = entry.find('atom:author', ns).find('atom:name', ns).text
            title = entry.find('atom:title', ns).text
            content = entry.find('atom:content', ns).text
            rating = int(rating_tag.text)
            version = entry.find('im:version', ns).text

            # Parse date
            try:
                # updated string is ISO 8601. 3.9+ supports fromisoformat.
                dt = datetime.datetime.fromisoformat(updated)
                # Ensure UTC
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                else:
                    dt = dt.astimezone(datetime.timezone.utc)
            except:
                dt = datetime.datetime.now(datetime.timezone.utc) # Fallback

            fetched_data.append({
                'source': 'ios',
                'id': review_id,
                'user_name': user_name,
                'date': dt,
                'rating': rating,
                'title': title,
                'content': content,
                'version': version,
                'country': country
            })

            if len(fetched_data) >= count:
                break

        return fetched_data

    except Exception as e:
        print(f"Error fetching iOS reviews (XML) for {country}: {e}")
        return []

def fetch_android_reviews(package_name, country, count=200):
    """
    Fetches reviews from Google Play Store.
    """
    try:
        lang = country if country in ['jp', 'en', 'ko'] else 'en'

        result, _ = gps_reviews(
            package_name,
            lang=lang,
            country=country,
            sort=Sort.NEWEST,
            count=count
        )

        fetched_data = []
        for r in result:
            dt = r.get('at')
            if dt:
                # Android scraper usually returns naive datetime (local time of the server? or UTC?)
                # Usually it's UTC but naive. Let's force UTC.
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                else:
                    dt = dt.astimezone(datetime.timezone.utc)

            fetched_data.append({
                'source': 'android',
                'id': r.get('reviewId'),
                'user_name': r.get('userName'),
                'date': dt,
                'rating': r.get('score'),
                'title': '',
                'content': r.get('content'),
                'version': r.get('reviewCreatedVersion', 'Unknown'), # Sometimes None
                'country': country
            })

        # Ensure version is not None
        for r in fetched_data:
            if r['version'] is None:
                r['version'] = 'Unknown'

        return fetched_data
    except Exception as e:
        print(f"Error fetching Android reviews for {country}: {e}")
        return []
