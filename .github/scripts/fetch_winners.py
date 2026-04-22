import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

def fetch_and_rank():
    # 1. Setup Credentials
    creds_json = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT'])
    if not creds_raw: return

    creds_dict = json.loads(creds_raw)
    creds = service_account.Credentials.from_service_account_info(
        creds_dict, scopes=['https://www.googleapis.com/auth/forms.responses.readonly']
    )
    service = build('forms', 'v1', credentials=creds)

    # 2. Get Data from GitHub Event
    form_id = os.environ.get('FORM_ID')
    poll_type = os.environ.get('POLL_TYPE')
    
    try:
        # Fetch responses from Google Forms
        result = service.forms().responses().list(formId=form_id).execute()
        responses = result.get('responses', [])
        
        output = f"## 🏆 Winners for {poll_type}\n"
        if not responses:
            output += "No votes were cast during the testing period."
        else:
            votes = {}
            for resp in responses:
                answer_values = list(resp['answers'].values())
                if answer_values:
                    # Capture Multiple Choices (Checkbox)
                    choices = answer_values[0]['textAnswers']['answers']
                    for c in choices:
                        val = c['value']
                        votes[val] = votes.get(val, 0) + 1

            sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            limit = 2 if "Long" in poll_type else 5
            
            for i, (title, count) in enumerate(sorted_votes[:limit], 1):
                output += f"{i}. **{title}** — ({count} votes) ✅\n"

        output += "\n---\n*Results generated automatically.*"
        
        # Save for the "create-comment" action to read
        with open("winner_summary.md", "w", encoding="utf-8") as f:
            f.write(output)

    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    fetch_and_rank()
