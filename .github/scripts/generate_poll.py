import os
import glob
import pandas as pd
import requests
import json
import re

# ENSURE THIS IS YOUR LATEST URL FROM GOOGLE APPS SCRIPT
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxYBHdnsIKVvdK1FJLMMsQdRiMA4qitvag4pZj6d9Z6NH18FDDCPnezGhQSQGbSRjej/exec"

def extract_form_id(url):
    """Robust extraction of Google Form ID from various URL formats."""
    if not url:
        return None
    # Captures the ID from /forms/d/e/.../viewform OR /forms/d/.../edit
    match = re.search(r"/d/(?:e/)?([^/]+)", url)
    if match:
        f_id = match.group(1)
        print(f"DEBUG: Extracted Form ID: {f_id}")
        return f_id
    print(f"DEBUG: Could not extract ID from URL: {url}")
    return None

def trigger_tally_workflow(form_id, poll_type):
    """Triggers the GitHub Action to fetch results in 2 minutes (for testing)."""
    github_token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    issue_number = os.environ.get("ISSUE_NUMBER", "0")
    
    if not github_token:
        print(f"❌ Missing GITHUB_TOKEN for {poll_type}")
        return
    if not repo:
        print(f"❌ Missing GITHUB_REPOSITORY for {poll_type}")
        return
    if not form_id:
        print(f"❌ Missing Form ID for {poll_type}")
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
            "issue_number": issue_number
        }
    }
    
    try:
        resp = requests.post(dispatch_url, headers=headers, json=payload, timeout=30)
        if resp.status_code == 204:
            print(f"✅ Tally workflow successfully triggered for {poll_type}")
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
        print(f"--- Starting Process for: {file_name} ---")
        
        # 1. Load and handle headers case-insensitively
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        # Verify required columns exist
        if 'TYPE' not in df.columns or 'TITLE' not in df.columns:
            raise ValueError(f"CSV missing 'TYPE' or 'TITLE' columns. Found: {list(df.columns)}")
        
        def get_titles(category):
            mask = df['TYPE'].astype(str).str.strip().str.upper() == category.upper()
            titles = df[mask]['TITLE'].dropna().unique().tolist()
            return [str(t).strip() for t in titles if str(t).strip()]

        video_titles = get_titles('V')
        shorts_titles = get_titles('S')

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"
        summary += "> 💡 *Winners will be posted here automatically after the 2-minute test period.*\n\n"

        for titles, label, icon in [(video_titles, "Long Video", "🎬"), (shorts_titles, "Shorts", "📱")]:
            if not titles:
                print(f"Notice: No titles found for {label}")
                continue

            print(f"Sending {len(titles)} titles for {label} to Google...")
            
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
                print(f"❌ Critical Error: Google returned HTML instead of JSON. Raw: {response.text[:200]}...")
                summary += f"⚠️ **{label}**: Connection error with Google Script.\n\n"
                continue

            if "error" in res_data:
                summary += f"⚠️ **{label}**: {res_data['error']}\n\n"
            else:
                form_url = res_data.get('url')
                summary += f"{icon} **{label} Poll**: [Vote Here]({form_url})\n"
                summary += f"📈 **Results**: [View Data](https://docs.google.com/spreadsheets/d/{res_data.get('sheetId', 'Check-Manual')})\n\n"
                
                # 3. Trigger the 2-minute tally action
                f_id = extract_form_id(form_url)
                trigger_tally_workflow(f_id, label)

        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
