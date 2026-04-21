import os
import glob
import pandas as pd
import requests

# PASTE YOUR WEB APP URL FROM STEP 1 HERE
WEB_APP_URL = "https://script.google.com/macros/s/AKfycby4oqGylkJM4PVPjhiQVP5upxAlMOM_DrjBWXx--JCCWlkRmu4DFrfMHPlYCjNCp1a7Cg/exec"

def main():
    try:
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files: return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        video_titles = df[df['TYPE'] == 'V']['TITLE'].dropna().unique().tolist()
        shorts_titles = df[df['TYPE'] == 'S']['TITLE'].dropna().unique().tolist()

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"

        for titles, label, icon in [(video_titles, "Long Video", "🎬"), (shorts_titles, "Shorts", "📱")]:
            if titles:
                response = requests.post(WEB_APP_URL, json={
                    "title": file_name,
                    "options": titles,
                    "type": label
                })
                res_data = response.json()
                summary += f"{icon} **{label} Poll:** [Vote Here]({res_data['url']})\n"
                summary += f"📈 **Results:** [View Data](https://docs.google.com/spreadsheets/d/{res_data['sheetId']})\n\n"

        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Error:** {str(e)}")

if __name__ == "__main__":
    main()
