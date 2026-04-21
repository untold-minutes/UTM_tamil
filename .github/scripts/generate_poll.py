import os
import glob
import pandas as pd
import requests
import json

# PASTE YOUR WEB APP URL HERE
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby6Dp1UG5URgTGEFRjOujy9DRoUSS_CiPgHaDg1fs96lxviN7H1KBXVPPU4eGx0XMKGEA/exec"

def main():
    try:
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files: return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        
        # Load CSV and force headers to uppercase
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        # FIX: Force 'TYPE' column to uppercase for matching
        def get_titles(category_code):
            if 'TYPE' not in df.columns or 'TITLE' not in df.columns:
                raise Exception("CSV missing 'TYPE' or 'TITLE' columns.")
            
            # This line handles v, V, s, or S
            mask = df['TYPE'].astype(str).str.strip().str.upper() == category_code.upper()
            titles = df[mask]['TITLE'].dropna().unique().tolist()
            return [str(t).strip() for t in titles if str(t).strip()]

        video_titles = get_titles('V')
        shorts_titles = get_titles('S')

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"

        for titles, label, icon in [(video_titles, "Long Video", "🎬"), (shorts_titles, "Shorts", "📱")]:
            # Always send the request so the Apps Script can create the file, 
            # even if the list is empty (it will now handle it gracefully)
            print(f"Processing {label}...")
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
