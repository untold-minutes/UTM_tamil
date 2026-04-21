import os
import glob
import pandas as pd
import requests

# Ensure this is the FRESH URL from the "New Version" deployment
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbz_zu20-xFXzeL4ENwWWZIfVtQdyiyw1aD2tD-NJ9s5EwwuHuabqE-9D0iCzb9kBu5FWQ/exec"

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
                }, timeout=30)
                
                # If Google sends an error page, this catches it
                if response.status_code != 200:
                    raise Exception(f"Google Script returned Status {response.status_code}. Full response: {response.text[:200]}")

                try:
                    res_data = response.json()
                except:
                    # This tells us EXACTLY what Google is sending back (likely a login page)
                    raise Exception(f"Received HTML instead of JSON. Check Deployment settings. Raw text: {response.text[:200]}")

                summary += f"{icon} **{label} Poll:** [Vote Here]({res_data['url']})\n"
                summary += f"📈 **Results:** [View Data](https://docs.google.com/spreadsheets/d/{res_data['sheetId']})\n\n"

        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Detailed Error:** {str(e)}")

if __name__ == "__main__":
    main()
