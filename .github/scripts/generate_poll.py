import os
import glob
import pandas as pd
import requests
import time

# Update with your LATEST Web App URL
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxYBHdnsIKVvdK1FJLMMsQdRiMA4qitvag4pZj6d9Z6NH18FDDCPnezGhQSQGbSRjej/exec"

def trigger_tally_workflow(form_id, poll_type):
    github_token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    issue_number = os.environ.get("ISSUE_NUMBER", "0")
    
    if not github_token or not repo or not form_id:
        print(f"❌ Skipping Tally Trigger for {poll_type}: Missing Env Vars or ID.")
        return

    dispatch_url = f"https://api.github.com/repos/{repo}/dispatches"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "event_type": "poll_started",
        "client_payload": {
            "form_id": str(form_id),
            "poll_type": str(poll_type),
            "issue_number": str(issue_number)
        }
    }
    
    resp = requests.post(dispatch_url, headers=headers, json=payload, timeout=30)
    if resp.status_code == 204:
        print(f"✅ Tally triggered for {poll_type}: {form_id}")
    else:
        print(f"❌ Dispatch Failed: {resp.status_code}")

def main():
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files: return
    
    latest_file = max(files, key=os.path.getmtime)
    file_name = os.path.basename(latest_file)
    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()

    summary = f"### 📊 New Content Polls for `{file_name}`\n\n"

    categories = [('V', "Long Video", "🎬"), ('S', "Shorts", "📱")]
    
    for i, (cat, label, icon) in enumerate(categories):
        mask = df['TYPE'].astype(str).str.strip().str.upper() == cat
        titles = df[mask]['TITLE'].dropna().unique().tolist()
        
        if not titles: continue

        # --- PREVENT DRIVE ERROR ---
        if i > 0:
            print("Waiting 3 seconds to avoid Google Drive rate limits...")
            time.sleep(3)

        print(f"Creating {label} poll...")
        response = requests.post(WEB_APP_URL, json={
            "title": file_name, "options": titles, "type": label
        }, timeout=60)
        
        res_data = response.json()
        if "url" in res_data:
            summary += f"{icon} **{label} Poll**: [Vote Here]({res_data['url']})\n\n"
            trigger_tally_workflow(res_data.get('formId'), label)
        else:
            summary += f"⚠️ **{label} Error**: {res_data.get('error')}\n\n"

    with open("poll_summary.md", "w", encoding="utf-8") as f:
        f.write(summary)

if __name__ == "__main__":
    main()
