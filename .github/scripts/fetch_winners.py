import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

def fetch_and_rank():
    # 1. Initialize variables early so they exist for the final save step
    winners_list = []
    output = ""
    poll_type = os.environ.get('POLL_TYPE', 'Shorts')
    form_id = os.environ.get('FORM_ID')
    
    try:
        # Setup Credentials
        creds_raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
        if not creds_raw or not form_id:
            print("❌ Missing GOOGLE_SERVICE_ACCOUNT or FORM_ID")
            return

        creds_dict = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/forms.responses.readonly']
        )
        service = build('forms', 'v1', credentials=creds)

        # 2. Fetch responses from Google Forms
        result = service.forms().responses().list(formId=form_id).execute()
        responses = result.get('responses', [])
        
        output = f"## 🏆 Winners for {poll_type}\n"
        type_code = "V" if "Long" in poll_type else "S"
        
        if not responses:
            output += "No votes were cast during the testing period."
        else:
            votes = {}
            for resp in responses:
                answer_values = list(resp['answers'].values())
                if answer_values:
                    choices = answer_values[0]['textAnswers']['answers']
                    for c in choices:
                        val = c['value']
                        votes[val] = votes.get(val, 0) + 1

            sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            limit = 2 if type_code == "V" else 5
            
            for i, (title, count) in enumerate(sorted_votes[:limit], 1):
                output += f"{i}. **{title}** — ({count} votes) ✅\n"
                # Store winner for the JSON file
                winners_list.append({
                    "type": type_code,
                    "title": title,
                    "rank": i
                })

        output += "\n---\n*Results generated automatically.*"

    except Exception as e:
        error_msg = f"❌ Error: {str(e)}"
        print(error_msg)
        output = f"## ❌ Tally Failed\n{error_msg}"

    # 3. SAVE PHASE: This must be OUTSIDE the try/except blocks
    # This ensures latest_winners.json is ALWAYS created
    with open("winner_summary.md", "w", encoding="utf-8") as f:
        f.write(output)
    
    with open("latest_winners.json", "w", encoding="utf-8") as f:
        json.dump(winners_list, f, indent=4)
        
    print(f"✅ Created latest_winners.json with {len(winners_list)} items.")

if __name__ == "__main__":
    fetch_and_rank()
