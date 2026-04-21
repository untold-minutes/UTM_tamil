import os
import glob
import pandas as pd
import requests

# PASTE YOUR NEW WEB APP URL HERE
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbyuNC7qT5g-baZve8t5Bb6I07o8JbdBZlSZBWrExu8UPxISgtiqZAnHuhYLhQFO8a3M/exec"

def main():
    try:
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files:
            print("No CSV files found.")
            return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        video_titles = df[df['TYPE'] == 'V']['TITLE'].dropna().unique().tolist()
        shorts_titles = df[df['TYPE'] == 'S']['TITLE'].dropna().unique().tolist()

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"

        for titles, label, icon in [(video_titles, "Long Video", "🎬"), (shorts_titles, "Shorts", "📱")]:
            if titles:
                # We use timeout and check the status code
                response = requests.post(WEB_APP_URL, json={
                    "title": file_name,
                    "options": titles,
                    "type": label
                }, timeout=30)
                
                # If the script fails, this will show us the HTML error
                if response.status_code != 200:
                    raise Exception(f"Apps Script returned Status {response.status_code}")

                res_data = response.json()
                summary += f"{icon} **{label} Poll:** [Vote Here]({res_data['url']})\n"
                summary += f"📈 **Results:** [View Data](https://docs.google.com/spreadsheets/d/{res_data['sheetId']})\n\n"

        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Error:** {str(e)}")
        print(f"Detailed Error: {e}")

if __name__ == "__main__":
    main()
