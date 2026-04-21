import os
import glob
import pandas as pd
import requests
import json

# ENSURE THIS IS THE URL YOU JUST TESTED
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbz_zu20-xFXzeL4ENwWWZIfVtQdyiyw1aD2tD-NJ9s5EwwuHuabqE-9D0iCzb9kBu5FWQ/exec"

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
                print(f"Sending request for {label}...")
                response = requests.post(WEB_APP_URL, json={
                    "title": file_name,
                    "options": titles,
                    "type": label
                }, timeout=60)
                
                # Parse the response safely
                try:
                    res_data = response.json()
                except Exception:
                    raise Exception(f"Apps Script sent back non-JSON text: {response.text[:200]}")

                # Check if the Apps Script reported an internal error
                if "error" in res_data:
                    raise Exception(f"Apps Script Error: {res_data['error']}")

                # Only try to access 'url' if it exists in the response
                if 'url' in res_data:
                    summary += f"{icon} **{label} Poll:** [Vote Here]({res_data['url']})\n"
                    summary += f"📈 **Results:** [View Data](https://docs.google.com/spreadsheets/d/{res_data['sheetId']})\n\n"
                else:
                    raise Exception(f"Response missing 'url'. Full data received: {res_data}")

        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Detailed Error:** {str(e)}")
        print(f"Detailed Log: {e}")

if __name__ == "__main__":
    main()
