import os
import glob
import pandas as pd
import requests
import json

# ENSURE THIS IS YOUR LATEST URL
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbxRKjzgG1AhkE2bcPNwyhFezT9ByeU3MBSUCiIyyLVjR4D1IiYa45sdnN3fQgkNqCM2aQ/exec"

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
            # Case-insensitive matching for 'v' or 's'
            mask = df['TYPE'].astype(str).str.strip().str.upper() == category.upper()
            titles = df[mask]['TITLE'].dropna().unique().tolist()
            return [str(t).strip() for t in titles if str(t).strip()]

        video_titles = get_titles('V')
        shorts_titles = get_titles('S')

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"

        for titles, label, icon in [(video_titles, "Long Video", "🎬"), (shorts_titles, "Shorts", "📱")]:
            # Debugging print to check titles before sending
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

        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Automation Error:** {str(e)}")

if __name__ == "__main__":
    main()
