import os
import json
import glob
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- CONFIGURATION ---
FOLDER_ID = "1tYV8MOD4AiCdWIMG_m_DwYjlxcEHOzBZ" 

def get_services():
    """Authenticates and returns the Google Cloud services."""
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS secret is missing!")
    
    creds_info = json.loads(creds_json)
    scopes = [
        'https://www.googleapis.com/auth/forms.body',
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/spreadsheets'
    ]
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
    
    return (
        build('forms', 'v1', credentials=creds),
        # FIXED: Service name is 'sheets', not 'spreadsheets'
        build('sheets', 'v4', credentials=creds),
        build('drive', 'v3', credentials=creds)
    )

def move_to_folder(d_service, file_id, folder_id):
    """Moves the created file into your UTM_Content_Planning folder."""
    file = d_service.files().get(fileId=file_id, fields='parents').execute()
    previous_parents = ",".join(file.get('parents'))
    d_service.files().update(
        fileId=file_id,
        addParents=folder_id,
        removeParents=previous_parents,
        fields='id, parents'
    ).execute()

def create_poll(f_service, s_service, d_service, title, options, type_label):
    """Creates a Sheet and Form, then moves them to the specified folder."""
    
    # 1. Create a New Google Sheet for results
    sheet_body = {'properties': {'title': f"Results - {type_label} - {title}"}}
    # Note: Even though service is 'sheets', the method is .spreadsheets()
    sheet = s_service.spreadsheets().create(body=sheet_body, fields='spreadsheetId').execute()
    sheet_id = sheet.get('spreadsheetId')
    move_to_folder(d_service, sheet_id, FOLDER_ID)

    # 2. Create the Google Form
    form_body = {"info": {"title": f"UTM Tamil: {type_label} Selection"}}
    form = f_service.forms().create(body=form_body).execute()
    form_id = form['formId']
    move_to_folder(d_service, form_id, FOLDER_ID)

    # 3. Add the Checkbox Question
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

    return form['responderUri'], sheet_id

def main():
    try:
        f_service, s_service, d_service = get_services()

        # Find latest CSV
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files:
            print("No CSV files found in src/01_Planning/")
            return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)

        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()

        video_titles = df[df['TYPE'].str.strip().upper() == 'V']['TITLE'].dropna().unique().tolist()
        shorts_titles = df[df['TYPE'].str.strip().upper() == 'S']['TITLE'].dropna().unique().tolist()

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"

        if video_titles:
            v_url, v_sheet = create_poll(f_service, s_service, d_service, file_name, video_titles, "Long Video")
            summary += f"🎬 **Long Video Poll:** [Vote Here]({v_url})\n"
            summary += f"📈 **Results Sheet:** [View Data](https://docs.google.com/spreadsheets/d/{v_sheet})\n\n"

        if shorts_titles:
            s_url, s_sheet = create_poll(f_service, s_service, d_service, file_name, shorts_titles, "Shorts")
            summary += f"📱 **Shorts Poll:** [Vote Here]({s_url})\n"
            summary += f"📈 **Results Sheet:** [View Data](https://docs.google.com/spreadsheets/d/{s_sheet})\n\n"

        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Error generating polls:** {str(e)}")
        print(f"Error details: {e}")

if __name__ == "__main__":
    main()
