import sys
import os
import json

# Wrap imports in a try-except to catch environment issues
try:
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    IMPORT_ERROR = None
except Exception as e:
    IMPORT_ERROR = str(e)

def main():
    # Force immediate output
    print("DEBUG: Script initialized")
    
    if IMPORT_ERROR:
        print(f"DEBUG: ❌ IMPORT ERROR: {IMPORT_ERROR}", flush=True)
        print("DEBUG: Ensure google-api-python-client is installed.", flush=True)
        sys.exit(1)

    workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
    json_path = os.path.join(workspace, "latest_winners.json")
    summary_path = os.path.join(workspace, "winner_summary.md")
    
    print(f"DEBUG: Workspace: {workspace}", flush=True)

    try:
        creds_raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
        form_id = os.environ.get('FORM_ID')
        poll_type = os.environ.get('POLL_TYPE', 'Shorts')

        if not creds_raw:
            print("DEBUG: ❌ GOOGLE_SERVICE_ACCOUNT is missing!")
            return

        print(f"DEBUG: Authenticating for Form ID: {form_id}", flush=True)
        creds_dict = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/forms.responses.readonly']
        )
        service = build('forms', 'v1', credentials=creds)

        print("DEBUG: Fetching responses...")
        result = service.forms().responses().list(formId=form_id).execute()
        responses = result.get('responses', [])
        
        winners_list = []
        summary_output = f"## 🏆 Winners for {poll_type}\n"
        type_code = "V" if "Long" in poll_type else "S"
        
        if not responses:
            print("DEBUG: ⚠️ No responses found.", flush=True)
            summary_output += "No votes were cast during the testing period."
        else:
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
                summary_output += f"{i}. **{title}** — ({count} votes) ✅\n"

        summary_output += "\n---\n*Results generated automatically.*"

        print(f"DEBUG: Writing JSON to {json_path}")
        
        # Load existing data to avoid overwriting results from other parallel polls
        current_data = []
        if os.path.exists(json_path):
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    current_data = json.load(f)
                    if not isinstance(current_data, list):
                        current_data = []
            except Exception:
                current_data = []

        # Remove old entries of the SAME type to refresh with new winners
        merged_data = [item for item in current_data if item.get("type") != type_code]
        merged_data.extend(winners_list)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(merged_data, f, indent=4, ensure_ascii=False)
            
        print(f"DEBUG: Writing Summary to {summary_path}")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary_output)
            
        print("DEBUG: ✅ Files Success.")

    except Exception as e:
        print(f"DEBUG: ❌ CRITICAL ERROR: {str(e)}")
        # If the file doesn't exist, create an empty list so the commit step doesn't fail
        if not os.path.exists(json_path):
            with open(json_path, "w") as f:
                f.write("[]")
        
        # If the summary doesn't exist, create an error message
        if not os.path.exists(summary_path):
            with open(summary_path, "w") as f:
                f.write(f"❌ Error fetching winners: {str(e)}\n\n*Please ensure the Service Account has permission to access the form.*")
        
        # Don't exit with 1, let the workflow finish so it can at least post the error comment
        return

if __name__ == "__main__":
    main()
