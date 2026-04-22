import sys
import os
import json

def log(msg):
    print(f"DEBUG: {msg}", file=sys.stderr, flush=True)

def fetch_and_rank():
    log("Checking Environment...")
    workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
    json_path = os.path.join(workspace, "latest_winners.json")
    
    try:
        log("Importing Google Libraries...")
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        log("Imports Successful.")

        creds_raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
        form_id = os.environ.get('FORM_ID')
        poll_type = os.environ.get('POLL_TYPE', 'Shorts')

        if not creds_raw:
            raise ValueError("GOOGLE_SERVICE_ACCOUNT is empty.")

        log(f"Processing Form: {form_id}")
        creds_dict = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/forms.responses.readonly']
        )
        service = build('forms', 'v1', credentials=creds)

        result = service.forms().responses().list(formId=form_id).execute()
        responses = result.get('responses', [])
        
        winners_list = []
        type_code = "V" if "Long" in poll_type else "S"
        
        if responses:
            votes = {}
            for resp in responses:
                answers = resp.get('answers', {})
                for ans_id, content in answers.items():
                    text_list = content.get('textAnswers', {}).get('answers', [])
                    for t in text_list:
                        val = t.get('value')
                        if val: votes[str(val)] = votes.get(str(val), 0) + 1

            sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            limit = 2 if type_code == "V" else 5
            
            for i, (title, count) in enumerate(sorted_votes[:limit], 1):
                winners_list.append({"type": type_code, "title": str(title), "rank": i})

        # ATOMIC WRITE
        log(f"Writing JSON to {json_path}")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(winners_list, f, indent=4, ensure_ascii=False)
        log("✅ JSON Success.")

    except Exception as e:
        log(f"❌ CRITICAL ERROR: {str(e)}")
        # Create an empty list file so the next step doesn't fail
        with open(json_path, "w") as f:
            f.write("[]")
        sys.exit(1)

if __name__ == "__main__":
    fetch_and_rank()
