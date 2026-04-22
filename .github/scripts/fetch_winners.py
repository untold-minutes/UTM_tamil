import os
import json
import traceback
from googleapiclient.discovery import build
from google.oauth2 import service_account

def fetch_and_rank():
    winners_list = []
    output = "## 📊 Poll Results\n"
    
    # Use explicit workspace path
    workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
    json_path = os.path.join(workspace, "latest_winners.json")
    md_path = os.path.join(workspace, "winner_summary.md")

    try:
        print("--- DEBUG: Starting Fetch ---")
        creds_raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
        form_id = os.environ.get('FORM_ID')
        poll_type = os.environ.get('POLL_TYPE', 'Shorts')

        creds_dict = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/forms.responses.readonly']
        )
        service = build('forms', 'v1', credentials=creds)

        result = service.forms().responses().list(formId=form_id).execute()
        responses = result.get('responses', [])
        
        type_code = "V" if "Long" in poll_type else "S"
        
        if not responses:
            output += "⚠️ No votes found."
        else:
            votes = {}
            for resp in responses:
                answers = resp.get('answers', {})
                for ans_id, content in answers.items():
                    text_answers = content.get('textAnswers', {}).get('answers', [])
                    for a in text_answers:
                        val = a.get('value')
                        if val:
                            votes[val] = votes.get(val, 0) + 1

            sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            limit = 2 if type_code == "V" else 5
            
            for i, (title, count) in enumerate(sorted_votes[:limit], 1):
                output += f"{i}. **{title}** — ({count} votes) ✅\n"
                winners_list.append({"type": type_code, "title": str(title), "rank": i})
        
        output += "\n---\n*Tally success.*"

    except Exception as e:
        print("--- DEBUG: SCRIPT CRASHED ---")
        print(traceback.format_exc())
        output += f"\n\n❌ ERROR: {str(e)}"

    # --- THE SAVE PHASE: ATOMIC ATTEMPT ---
    print(f"--- DEBUG: Attempting to write JSON to {json_path} ---")
    try:
        json_data = json.dumps(winners_list, indent=4, ensure_ascii=False)
        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json_data)
            f.flush()
            os.fsync(f.fileno()) # Force write to disk
        print("✅ JSON file write completed.")
    except Exception as je:
        print(f"❌ JSON WRITE FAILED: {str(je)}")

    print(f"--- DEBUG: Attempting to write MD to {md_path} ---")
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(output)
            f.flush()
            os.fsync(f.fileno())
        print("✅ MD file write completed.")
    except Exception as me:
        print(f"❌ MD WRITE FAILED: {str(me)}")

if __name__ == "__main__":
    fetch_and_rank()
