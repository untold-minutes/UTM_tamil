import os
import json
import glob
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build

def get_google_service():
    creds_json = os.getenv("GOOGLE_CREDENTIALS")
    if not creds_json:
        raise ValueError("GOOGLE_CREDENTIALS secret is missing!")
    
    creds_info = json.loads(creds_json)
    scopes = ['https://www.googleapis.com/auth/forms.body', 'https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_info(creds_info, scopes=scopes)
    return build('forms', 'v1', credentials=creds)

def create_google_form(service, title, options, type_name):
    """Creates a Google Form with a Multi-Select (Checkbox) question."""
    # 1. Create the Form
    form_body = {"info": {"title": f"UTM Tamil: {type_name} Selection - {title}"}}
    form = service.forms().create(body=form_body).execute()
    form_id = form['formId']

    # 2. Add the Checkbox Question
    update = {
        "requests": [{
            "createItem": {
                "item": {
                    "title": f"Which {type_name} stories should we create next? (Select all you like)",
                    "questionItem": {
                        "question": {
                            "required": True,
                            "choiceQuestion": {
                                "type": "CHECKBOX", # Multiple selection enabled
                                "options": [{"value": opt} for opt in options]
                            }
                        }
                    }
                },
                "location": {"index": 0}
            }
        }]
    }
    service.forms().batchUpdate(formId=form_id, body=update).execute()
    return form['responderUri']

def main():
    service = get_google_service()

    # Find the latest planning CSV
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        print("No planning files found.")
        return
    latest_file = max(files, key=os.path.getmtime)
    file_label = os.path.basename(latest_file)

    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()

    # Separate Shorts (S) and Videos (V)
    shorts = df[df['TYPE'].str.strip().str.upper() == 'S']['TITLE'].dropna().unique().tolist()
    videos = df[df['TYPE'].str.strip().str.upper() == 'V']['TITLE'].dropna().unique().tolist()

    # Generate Poll 1: Videos
    if videos:
        video_url = create_google_form(service, file_label, videos[:15], "Long Video")
        print(f"🎬 VIDEO POLL CREATED: {video_url}")

    # Generate Poll 2: Shorts
    if shorts:
        shorts_url = create_google_form(service, file_label, shorts[:15], "Shorts")
        print(f"📱 SHORTS POLL CREATED: {shorts_url}")

if __name__ == "__main__":
    main()
