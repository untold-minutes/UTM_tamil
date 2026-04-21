import os
import glob
import pandas as pd
import requests
import json

# Replace with your NEW Deployment URL from Google Apps Script
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxYBHdnsIKVvdK1FJLMMsQdRiMA4qitvag4pZj6d9Z6NH18FDDCPnezGhQSQGbSRjej/exec"

def trigger_tally_workflow(form_id, poll_type):
    """
    Sends the Internal Form ID to GitHub Actions to trigger the 2-minute 
    tally/fetch_winners script.
    """
    github_token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    issue_number = os.environ.get("ISSUE_NUMBER", "0")
    
    if not github_token or not repo or not form_id:
        print(f"❌ Skipping Tally Trigger for {poll_type}: Missing environment variables or ID.")
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
        resp = requests.post(dispatch_url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 204:
            print(f"✅ Tally workflow successfully triggered for {poll_type} (ID: {form_id})")
        else:
            print(f"❌ GitHub Dispatch Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Error triggering Dispatch: {str(e)}")

def main():
    try:
        # 1. Locate the latest CSV file
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files:
            print("No CSV files found in src/01_Planning/")
            return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        print(f"--- Processing: {file_name} ---")
        
        # 2. Load and clean data
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        if 'TYPE' not in df.columns or 'TITLE' not in df.columns:
            raise ValueError(f"CSV missing columns. Found: {list(df.columns)}")
        
        def get_titles(category):
            mask = df['TYPE'].astype(str).str.strip().str.upper() == category.upper()
            titles = df[mask]['TITLE'].dropna().unique().tolist()
            return [str(t).strip() for t in titles if str(t).strip()]

        video_titles = get_titles('V')
        shorts_titles = get_titles('S')

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"
        summary += "> 💡 *Winners will be posted here automatically after the testing period.*\n\n"

        # 3. Create Polls via Google Apps Script
        for titles, label, icon in [(video_titles, "Long Video", "🎬"), (shorts_titles, "Shorts", "📱")]:
            if not titles:
                print(f"Notice: No titles found for {label}")
                continue

            print(f"Sending {len(titles)} titles for {label} to Google...")
            
            response = requests.post(
                WEB_APP_URL, 
                json={"title": file_name, "options": titles, "type": label}, 
                timeout=60
            )
            
            try:
                res_data = response.json()
            except Exception:
                print(f"❌ Google Error: HTML returned instead of JSON.")
                summary += f"⚠️ **{label}**: Connection error.\n\n"
                continue

            if "error" in res_data:
                summary += f"⚠️ **{label}**: {res_data['error']}\n\n"
            else:
                form_url = res_data.get('url')
                form_id = res_data.get('formId') # The Internal API ID
                
                summary += f"{icon} **{label} Poll**: [Vote Here]({form_url})\n"
                summary += f"📈 **Results**: [View Data](https://docs.google.com/spreadsheets/d/{res_data.get('sheetId', 'manual')})\n\n"
                
                # 4. Trigger the Fetch/Tally script using the INTERNAL ID
                trigger_tally_workflow(form_id, label)

        # 5. Save summary for GitHub Comment
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
        print("--- Process Complete: poll_summary.md generated ---")

    except Exception as e:
        print(f"❌ MAIN ERROR: {str(e)}")
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Automation Error**: {str(e)}")

if __name__ == "__main__":
    main()
