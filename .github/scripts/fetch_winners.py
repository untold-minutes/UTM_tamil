import os
import json
import sys

def fetch_and_rank():
    # 1. Immediate Path Setup
    workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
    json_path = os.path.join(workspace, "latest_winners.json")
    md_path = os.path.join(workspace, "winner_summary.md")
    
    winners_list = []
    output = "## 📊 Poll Results\n"

    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        creds_raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
        form_id = os.environ.get('FORM_ID')
        poll_type = os.environ.get('POLL_TYPE', 'Shorts')

        # 2. Setup Google Service
        creds_dict = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/forms.responses.readonly']
        )
        service = build('forms', 'v1', credentials=creds)

        # 3. Fetch Data
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
                        if val: votes[val] = votes.get(val, 0) + 1

            sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            limit = 2 if type_code == "V" else 5
            
            for i, (title, count) in enumerate(sorted_votes[:limit], 1):
                output += f"{i}. **{title}** — ({count} votes) ✅\n"
                winners_list.append({"type": type_code, "title": str(title), "rank": i})
        
        output += "\n---\nTally successful."

    except Exception as e:
        # If anything fails, we catch it here
        output += f"\n\n❌ ERROR: {str(e)}"
        print(f"CRITICAL ERROR: {str(e)}", file=sys.stderr)

    # 4. THE ABSOLUTE SAVE
    # We write JSON first. If this fails, the whole script should crash visibly.
    print(f"Writing JSON to {json_path}...")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(winners_list, f, indent=4, ensure_ascii=False)
    
    print(f"Writing MD to {md_path}...")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(output)

    print("✅ Done.")

if __name__ == "__main__":
    fetch_and_rank()
