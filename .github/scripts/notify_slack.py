import os
import json
import urllib.request
import sys

def send_slack_notification():
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if not webhook_url:
        print("Error: SLACK_WEBHOOK_URL is not set.")
        sys.exit(1)

    pr_title = os.environ.get('PR_TITLE', 'Unknown Title')
    pr_body = os.environ.get('PR_BODY') or 'No description provided.'
    pr_url = os.environ.get('PR_URL', '')
    pr_author = os.environ.get('PR_AUTHOR', 'Unknown')

    # Truncate body if it's too long to avoid Slack errors (block text limit is 3000)
    if len(pr_body) > 2900:
        pr_body = pr_body[:2900] + "...(truncated)"

    # Construct the payload
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": ":merged: PR Merged: " + pr_title,
                    "emoji": True
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Author:*\n{pr_author}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*URL:*\n<{pr_url}|View Pull Request>"
                    }
                ]
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Description:*"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": pr_body
                }
            }
        ]
    }

    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )

    try:
        with urllib.request.urlopen(req) as response:
            print(f"Notification sent successfully. Status: {response.getcode()}")
    except urllib.error.HTTPError as e:
        print(f"Failed to send notification. Error: {e.code} {e.reason}")
        print(e.read().decode())
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Failed to send notification. Error: {e.reason}")
        sys.exit(1)

if __name__ == "__main__":
    send_slack_notification()
