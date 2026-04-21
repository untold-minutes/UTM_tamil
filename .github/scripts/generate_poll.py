import os
import json
import glob
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- CONFIGURATION ---
FOLDER_ID = "1tYV8MOD4AiCdWIMG_m_DwYjlxcEHOzBZ" 
# PASTE YOUR TEMPLATE IDS HERE
SHEET_TEMPLATE_ID = "YOUR_TEMPLATE_SHEET_ID_HERE"
FORM_TEMPLATE_ID = "YOUR_TEMPLATE_FORM_ID_HERE"

def get_services():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS secret is missing!")
    creds_info = json.loads(creds_json)
    scopes = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/forms.body', 'https://www.googleapis.com/auth/spreadsheets']
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
    return build('forms', 'v1', credentials=creds), build('drive', 'v3', credentials=creds)

def create_poll(f_service, d_service, title, options, type_label):
    # 1. COPY the Template Sheet (inherits your quota)
    sheet_copy = d_service.files().copy(
        fileId=SHEET_TEMPLATE_ID,
        body={'name': f"Results - {type_label} - {title}", 'parents': [FOLDER_ID]}
    ).execute()
    sheet_id = sheet_copy.get('id')

    # 2. COPY the Template Form (inherits your quota)
    form_copy = d_service.files().copy(
        fileId=FORM_TEMPLATE_ID,
        body={'name': f"UTM Tamil: {type_label} Selection", 'parents': [FOLDER_ID]}
    ).execute()
    form_id = form_copy.get('id')

    # 3. Add Questions to the newly copied Form
    update = {
        "requests": [{
            "createItem": {
                "item": {
                    "title": f"Which {type_label} stories should we create next?",
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {
                                "type": "CHECKBOX",
                                "options": [{"value": opt} for opt in options]
                            }
                        }
                    }
                },
                "location": {"index": 0}
            }
        }]
    }
    f_service.forms().batchUpdate(formId=form_id, body=update).execute()

    final_form = f_service.forms().get(formId=form_id).execute()
    return final_form['responderUri'], sheet_id

def main():
    try:
        f_service, d_service = get_services()
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files: return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        df['TYPE'] = df['TYPE'].astype(str).str.strip().str.upper()

        v_titles = df[df['TYPE'] == 'V']['TITLE'].dropna().unique().tolist()
        s_titles = df[df['TYPE'] == 'S']['TITLE'].dropna().unique().tolist()

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"
        if v_titles:
            url, sheet = create_poll(f_service, d_service, file_name, v_titles, "Long Video")
            summary += f"🎬 **Long Video Poll:** [Vote Here]({url})\n📈 **Results:** [View Data](https://docs.google.com/spreadsheets/d/{sheet})\n\n"
        if s_titles:
            url, sheet = create_poll(f_service, d_service, file_name, s_titles, "Shorts")
            summary += f"📱 **Shorts Poll:** [Vote Here]({url})\n📈 **Results:** [View Data](https://docs.google.com/spreadsheets/d/{sheet})\n\n"

        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Error:** {str(e)}")

if __name__ == "__main__":
    main()
