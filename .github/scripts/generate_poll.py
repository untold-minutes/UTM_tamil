import os
import json
import glob
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

# --- CONFIGURATION ---
# Your UTM_Content_Planning Folder ID
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
        build('sheets', 'v4', credentials=creds),
        build('drive', 'v3', credentials=creds)
    )

def create_poll(f_service, s_service, d_service, title, options, type_label):
    """Creates files directly inside the shared folder to bypass quota limits."""
    
    # 1. Create the Google Sheet directly in the folder
    sheet_metadata = {
        'name': f"Results - {type_label} - {title}",
        'mimeType': 'application/vnd.google-apps.spreadsheet',
        'parents': [FOLDER_ID]
    }
    
    sheet_file = d_service.files().create(
        body=sheet_metadata,
        supportsAllDrives=True,
        fields='id'
    ).execute()
    sheet_id = sheet_file.get('id')

    # 2. Create the Google Form directly in the folder
    form_metadata = {
        'name': f"UTM Tamil: {type_label} Selection",
        'mimeType': 'application/vnd.google-apps.form',
        'parents': [FOLDER_ID]
    }
    
    form_file = d_service.files().create(
        body=form_metadata,
        supportsAllDrives=True,
        fields='id'
    ).execute()
    form_id = form_file.get('id')

    # 3. Add the Checkbox Question to the Form
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

    # Get the responder URL for the GitHub comment
    final_form = f_service.forms().get(formId=form_id).execute()
    return final_form['responderUri'], sheet_id

def main():
    try:
        f_service, s_service, d_service = get_services()

        # Find the latest CSV in the planning folder
        path = "src/01_Planning/*.csv"
        files = glob.glob(path)
        if not files:
            print("No CSV files found in src/01_Planning/")
            return
        
        latest_file = max(files, key=os.path.getmtime)
        file_name = os.path.basename(latest_file)

        # Load and clean the CSV data
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        # Ensure TYPE column is uppercase and string-based
        df['TYPE'] = df['TYPE'].astype(str).str.strip().str.upper()

        video_titles = df[df['TYPE'] == 'V']['TITLE'].dropna().unique().tolist()
        shorts_titles = df[df['TYPE'] == 'S']['TITLE'].dropna().unique().tolist()

        summary = f"### 📊 New Content Polls for `{file_name}`\n\n"

        if video_titles:
            v_url, v_sheet = create_poll(f_service, s_service, d_service, file_name, video_titles, "Long Video")
            summary += f"🎬 **Long Video Poll:** [Vote Here]({v_url})\n"
            summary += f"📈 **Results Sheet:** [View Data](https://docs.google.com/spreadsheets/d/{v_sheet})\n\n"

        if shorts_titles:
            s_url, s_sheet = create_poll(f_service, s_service, d_service, file_name, shorts_titles, "Shorts")
            summary += f"📱 **Shorts Poll:** [Vote Here]({s_url})\n"
            summary += f"📈 **Results Sheet:** [View Data](https://docs.google.com/spreadsheets/d/{s_sheet})\n\n"

        # Write to the summary file for the GitHub Action to post
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(summary)
            
    except Exception as e:
        # If any error occurs, output it to the summary so you can see it on GitHub
        with open("poll_summary.md", "w", encoding="utf-8") as f:
            f.write(f"❌ **Error generating polls:** {str(e)}")
        print(f"Detailed Error: {e}")

if __name__ == "__main__":
    main()
