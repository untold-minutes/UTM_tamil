import os
import glob
import pandas as pd
import requests
import json

# PASTE YOUR WEB APP URL HERE
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby6Dp1UG5URgTGEFRjOujy9DRoUSS_CiPgHaDg1fs96lxviN7H1KBXVPPU4eGx0XMKGEA/exec"

def main():
    try:
        # 1. Find the latest planning CSV
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files:
            print("No CSV files found.")
            return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        
        # 2. Load and clean CSV columns
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        # 3. Clean and Extract Titles (Ensuring strings only, no empty values)
        def clean_titles(filter_type):
            titles = df[df['TYPE'].astype(str).str.strip().str.upper() == filter_type]['TITLE']
            return [str(t).strip() for t in titles.dropna().unique().tolist() if str(t).strip()]

        video_titles = clean_titles('V')
        shorts_titles = clean_titles('S')

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"

        # 4. Trigger Apps Script for each category
        categories = [
            (video_titles, "Long Video", "🎬"),
            (shorts_titles, "Shorts", "📱")
        ]

        for titles, label, icon in categories:
            if titles:
                print(f"Requesting poll for {label}...")
                response = requests.post(WEB_APP_URL, json={
                    "title": file_name,
                    "options": titles,
                    "type": label
                }, timeout=60)
                
                if response.status_code != 200:
                    raise Exception(f"HTTP {response.status_code}: {response.text[:100]}")

                res_data = response.json()
                
                if "error" in res_data:
                    raise Exception(f"Apps Script Error: {res_data['error']}")

                summary += f"{icon} **{label} Poll:** [Vote Here]({res_data['url']})\n"
                summary += f"📈 **Results:** [View Data](https://docs.google.com/spreadsheets/d/{res_data['sheetId']})\n\n"

        # 5. Save summary for GitHub Comment
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        error_msg = f"❌ **Automation Error:** {str(e)}"
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(error_msg)
        print(error_msg)

if __name__ == "__main__":
    main()
