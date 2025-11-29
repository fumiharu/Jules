# Google Cloud Storage Setup Guide

To run this application, you need a Google Cloud Storage (GCS) bucket and a Service Account with permission to write to it.

## 1. Create a Project
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project (e.g., `app-review-viewer`).

## 2. Create a Storage Bucket
1. In the sidebar, navigate to **Cloud Storage** > **Buckets**.
2. Click **CREATE**.
3. Enter a unique name (e.g., `my-app-reviews-data`).
4. Choose `Region` (e.g., `asia-northeast1` for Tokyo) for lower latency if you are in Japan.
5. Keep other settings as default and click **CREATE**.

## 3. Create a Service Account
1. Navigate to **IAM & Admin** > **Service Accounts**.
2. Click **CREATE SERVICE ACCOUNT**.
3. Name it (e.g., `github-actions-uploader`).
4. Grant this service account the role **Storage Object Admin** (allows reading and writing objects).
5. Click **DONE**.

## 4. Generate a Key (JSON)
1. Click on the newly created service account in the list.
2. Go to the **KEYS** tab.
3. Click **ADD KEY** > **Create new key**.
4. Select **JSON** and click **CREATE**.
5. A JSON file will be downloaded to your computer. **Keep this safe!**

## 5. Configure GitHub Secrets (For GitHub Actions)
1. Go to your GitHub repository settings.
2. Navigate to **Secrets and variables** > **Actions**.
3. Add a new repository secret:
   - Name: `GCS_SERVICE_ACCOUNT_KEY`
   - Value: (Paste the entire content of the JSON file you downloaded)
4. Add another secret:
   - Name: `GCS_BUCKET_NAME`
   - Value: (The name of the bucket you created in step 2)

## 6. Local Execution Setup
To run the script or web app locally with GCS access:
1. Set the environment variable `GOOGLE_APPLICATION_CREDENTIALS` to the path of your JSON key file.
   ```bash
   export GOOGLE_APPLICATION_CREDENTIALS="/path/to/key.json"
   ```
2. Or, run the collector in "local mode" (saves to local disk instead of GCS):
   ```bash
   python src/collector/main.py --local
   ```
