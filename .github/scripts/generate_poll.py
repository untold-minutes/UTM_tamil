import os
import glob
import pandas as pd
import requests
import json
import re

# ENSURE THIS IS YOUR LATEST URL
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxRKjzgG1AhkE2bcPNwyhFezT9ByeU3MBSUCiIyyLVjR4D1IiYa45sdnN3fQgkNqCM2aQ/exec"

def extract_form_id(url):
    """Extracts the unique ID from a Google Form URL."""
    if not url:
        return None
    match = re.search(r"/forms/d/e/(.*?)/viewform", url)
    return match.group(1) if match else None

def trigger_tally_workflow(form_id, poll_type):
    """Triggers the GitHub Action to fetch results."""
    github_token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    
    if not github_token or not repo or not form_id:
        print(f"Skipping tally trigger for {poll_type}: Missing credentials or ID")
        return

    dispatch_url = f"https://api.github.com/repos/{repo}/dispatches"
    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    payload = {
        "event_type": "poll_started",
        "client_payload": {
            "form_id": form_id,
            "poll_type": poll_type,
            "issue_number": os.environ.get("ISSUE_NUMBER", "0") 
        }
    }
    
    try:
        resp = requests.post(dispatch_url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 204:
            print(f"✅ Tally workflow triggered for {poll_type}")
        else:
            print(f"❌ GitHub Dispatch Failed: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"❌ Error triggering Dispatch: {str(e)}")

def main():
    try:
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files:
            print("No CSV files found in src/01_Planning/")
            return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        print(f"Processing: {file_name}")
        
        # 1. Load and handle headers case-insensitively
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        # Verify required columns exist
        required = {'TYPE', 'TITLE'}
        if not required.issubset(df.columns):
            raise ValueError(f"CSV missing required columns. Found: {list(df.columns)}")
        
        def get_titles(category):
            # Case-insensitive match for values (v vs V)
            mask = df['TYPE'].astype(str).str.strip().str.upper() == category.upper()
            titles = df[mask]['TITLE'].dropna().unique().tolist()
            return [str(t).strip() for t in titles if str(t).strip()]

        video_titles = get_titles('V')
        shorts_titles = get_titles('S')

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"
        summary += "> 💡 *Winners will be posted here automatically after the test period.*\n\n"

        for titles, label, icon in [(video_titles, "Long Video", "🎬"), (shorts_titles, "Shorts", "📱")]:
            if not titles:
                print(f"No titles found for {label}")
                continue

            num_titles = len(titles)
            print(f"Sending {num_titles} titles for {label} to Google...")
            
            response = requests.post(
                WEB_APP_URL, 
                json={
                    "title": file_name,
                    "options": titles,
                    "type": label
                }, 
                timeout=60
            )
            
            try:
                res_data = response.json()
            except Exception:
                print(f"❌ Critical Error: Google did not return JSON. Raw output: {response.text}")
                summary += f"⚠️ **{label}**: Google connection error. Check Deployment URL.\n\n"
                continue

            if "error" in res_data:
                summary += f"⚠️ **{label}**: {res_data['error']}\n\n"
            else:
                summary += f"{icon} **{label} Poll**: [Vote Here]({res_data['url']})\n"
                # sheetId is manually linked in our current GAS fix, but we keep the URL structure
                summary += f"📈 **Results**: [View Data](https://docs.google.com/spreadsheets/d/{res_data.get('sheetId', 'manual')})\n\n"
                
                # 3. Trigger Tally
                f_id = extract_form_id(res_data.get('url'))
                if f_id:
                    trigger_tally_workflow(f_id, label)

        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        print(f"❌ MAIN ERROR: {str(e)}")
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Automation Error**: {str(e)}")

if __name__ == "__main__":
    main()
