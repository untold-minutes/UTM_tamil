import os
import glob
import pandas as pd
import requests
import time
import json

# IMPORTANT: Ensure this is the "Anyone" access URL from your latest deployment
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxYBHdnsIKVvdK1FJLMMsQdRiMA4qitvag4pZj6d9Z6NH18FDDCPnezGhQSQGbSRjej/exec"

def trigger_tally_workflow(form_id, poll_type):
    """Triggers the poll_started dispatch to GitHub Actions"""
    github_token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    issue_number = os.environ.get("ISSUE_NUMBER", "0")
    
    if not github_token or not repo or not form_id:
        print(f"⚠️ Tally skipped for {poll_type}: Missing env data.")
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
    
    try:
        r = requests.post(dispatch_url, headers=headers, json=payload, timeout=30)
        if r.status_code == 204:
            print(f"✅ Dispatch sent for {poll_type}")
        else:
            print(f"❌ Dispatch failed ({r.status_code}): {r.text}")
    except Exception as e:
        print(f"❌ Error triggering dispatch: {e}")

def main():
    try:
        # 1. Find CSV
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files:
            print("❌ No CSV found in src/01_Planning/")
            return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        print(f"--- Processing: {file_name} ---")
        
        # 2. Load Data
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        summary = f"### 📊 New Content Polls: `{file_name}`\n\n"
        categories = [('V', "Long Video", "🎬"), ('S', "Shorts", "📱")]

        for i, (cat_code, label, icon) in enumerate(categories):
            mask = df['TYPE'].astype(str).str.strip().str.upper() == cat_code
            titles = df[mask]['TITLE'].dropna().unique().tolist()
            
            if not titles:
                continue

            # Pause to prevent Google Drive "Service Error" (Folder lock)
            if i > 0:
                print("Waiting 3s for Google Drive stability...")
                time.sleep(3)

            print(f"🚀 Sending {label} to Google Apps Script...")
            
            try:
                response = requests.post(
                    WEB_APP_URL, 
                    json={"title": file_name, "options": titles, "type": label},
                    timeout=60
                )
                
                # CHECK: Did Google actually send a valid response?
                if response.status_code != 200:
                    print(f"❌ Google Error {response.status_code}: {response.text[:200]}")
                    summary += f"⚠️ **{label}**: Connection failed (Code {response.status_code})\n\n"
                    continue

                # CHECK: Is it valid JSON?
                try:
                    res_data = response.json()
                except json.JSONDecodeError:
                    print(f"❌ Google returned HTML instead of JSON. Check 'Anyone' permissions.")
                    print(f"DEBUG RAW RESPONSE: {response.text[:500]}")
                    summary += f"⚠️ **{label}**: Google returned an error page.\n\n"
                    continue

                # PROCESS SUCCESS
                if "url" in res_data:
                    summary += f"{icon} **{label} Poll**: [Vote Here]({res_data['url']})\n\n"
                    trigger_tally_workflow(res_data.get('formId'), label)
                else:
                    summary += f"⚠️ **{label}**: {res_data.get('error', 'Unknown Error')}\n\n"

            except Exception as e:
                print(f"❌ Request Error: {e}")
                summary += f"⚠️ **{label}**: Script crashed.\n\n"

        # 3. Save Summary
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
        print("--- All Done! Summary generated. ---")

    except Exception as e:
        print(f"❌ Critical Error: {e}")

if __name__ == "__main__":
    main()
