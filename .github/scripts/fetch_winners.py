import sys
import os
import json

# 1. IMMEDIATE LOGGING TO STDERR
def log(msg):
    print(f"DEBUG: {msg}", file=sys.stderr, flush=True)

log("Script execution started")

def fetch_and_rank():
    workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
    json_path = os.path.join(workspace, "latest_winners.json")
    md_path = os.path.join(workspace, "winner_summary.md")
    
    log(f"Workspace: {workspace}")
    
    # 2. CREATE DUMMY JSON IMMEDIATELY
    # This proves the script has write access to the root
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump([{"status": "initializing"}], f)
        log("✅ Dummy JSON created successfully")
    except Exception as e:
        log(f"❌ Failed to create Dummy JSON: {e}")

    winners_list = []
    output = "## 📊 Poll Results\n"

    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        creds_raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
        form_id = os.environ.get('FORM_ID')
        poll_type = os.environ.get('POLL_TYPE', 'Shorts')

        if not creds_raw:
            log("❌ GOOGLE_SERVICE_ACCOUNT is missing")
            return

        log("Attempting Google API Connection")
        creds_dict = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/forms.responses.readonly']
        )
        service = build('forms', 'v1', credentials=creds)

        result = service.forms().responses().list(formId=form_id).execute()
        responses = result.get('responses', [])
        type_code = "V" if "Long" in poll_type else "S"
        
        if not responses:
            output += "No votes found."
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
                output += f"{i}. **{title}** — ({count} votes) ✅\n"
                winners_list.append({"type": type_code, "title": str(title), "rank": i})
        
        output += "\n---\nTally successful."
        log(f"Tally complete: {len(winners_list)} winners found")

    except Exception as e:
        log(f"❌ CRITICAL ERROR: {str(e)}")
        output += f"\n\n❌ ERROR: {str(e)}"

    # 3. FINAL OVERWRITE
    try:
        log("Writing final JSON...")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(winners_list, f, indent=4, ensure_ascii=False)
        
        log("Writing final MD...")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(output)
        log("✅ All files written")
    except Exception as e:
        log(f"❌ Final write failed: {e}")

if __name__ == "__main__":
    fetch_and_rank()
