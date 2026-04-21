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
    match = re.search(r"/forms/d/e/(.*?)/viewform", url)
    return match.group(1) if match else None

def trigger_tally_workflow(form_id, poll_type):
    """Triggers the GitHub Action to fetch results in 24 hours."""
    github_token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY") # Format: 'username/repo'
    
    if not github_token or not repo or not form_id:
        print(f"Skipping tally trigger: Missing credentials or Form ID for {poll_type}")
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
            # Pass the run ID or Issue number if you want to comment on a specific place
            "issue_number": os.environ.get("ISSUE_NUMBER", "0") 
        }
    }
    
    requests.post(dispatch_url, headers=headers, json=payload)
    print(f"✅ Tally workflow triggered for {poll_type}")

def main():
    try:
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files: return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        
        # Load and fix headers
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        def get_titles(category):
            mask = df['TYPE'].astype(str).str.strip().str.upper() == category.upper()
            titles = df[mask]['TITLE'].dropna().unique().tolist()
            return [str(t).strip() for t in titles if str(t).strip()]

        video_titles = get_titles('V')
        shorts_titles = get_titles('S')

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"
        summary += "> 💡 *Winners (Top 2 Videos / Top 7 Shorts) will be posted here automatically in 24 hours.*\n\n"

        for titles, label, icon in [(video_titles, "Long Video", "🎬"), (shorts_titles, "Shorts", "📱")]:
            if not titles:
                continue

            print(f"Sending {len(titles)} titles for {label}")
            
            response = requests.post(WEB_APP_URL, json={
                "title": file_name,
                "options": titles,
                "type": label
            }, timeout=60)
            
            res_data = response.json()
            if "error" in res_data:
                summary += f"⚠️ **{label}:** {res_data['error']}\n\n"
            else:
                summary += f"{icon} **{label} Poll:** [Vote Here]({res_data['url']})\n"
                summary += f"📈 **Results:** [View Data](https://docs.google.com/spreadsheets/d/{res_data['sheetId']})\n\n"
                
                # Trigger the 24-hour tally workflow
                f_id = extract_form_id(res_data['url'])
                trigger_tally_workflow(f_id, label)

        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Automation Error:** {str(e)}")

if __name__ == "__main__":
    main()
