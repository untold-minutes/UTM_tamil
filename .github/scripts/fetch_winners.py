import os
import json
from googleapiclient.discovery import build
from google.oauth2 import service_account

def fetch_and_rank():
    # 1. Initialize data early to ensure files are created even if the API fails
    winners_list = []
    output = "## 📊 Poll Results\n"
    
    # Force paths to the repository root using GITHUB_WORKSPACE
    workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
    json_path = os.path.join(workspace, "latest_winners.json")
    md_path = os.path.join(workspace, "winner_summary.md")

    try:
        # Get Environment Variables
        creds_raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
        form_id = os.environ.get('FORM_ID')
        poll_type = os.environ.get('POLL_TYPE', 'Shorts')

        if not creds_raw or not form_id:
            raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT or FORM_ID in environment.")

        # Setup Google Service
        creds_dict = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/forms.responses.readonly']
        )
        service = build('forms', 'v1', credentials=creds)

        # 2. Fetch responses from Google Forms
        result = service.forms().responses().list(formId=form_id).execute()
        responses = result.get('responses', [])
        
        output = f"## 🏆 Winners for {poll_type}\n"
        # Prefix: V for Long Videos, S for Shorts
        type_code = "V" if "Long" in poll_type else "S"
        
        if not responses:
            output += "No votes were cast during this period. Defaulting to empty winners list."
        else:
            votes = {}
            for resp in responses:
                # Standard Google Forms response parsing
                answer_values = list(resp.get('answers', {}).values())
                if answer_values:
                    # Checkbox/Multiple choice results
                    choices = answer_values[0].get('textAnswers', {}).get('answers', [])
                    for c in choices:
                        val = c.get('value')
                        if val:
                            votes[val] = votes.get(val, 0) + 1

            # Sort by highest vote count
            sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            limit = 2 if type_code == "V" else 5
            
            for i, (title, count) in enumerate(sorted_votes[:limit], 1):
                output += f"{i}. **{title}** — ({count} votes) ✅\n"
                # This is the data the merge script needs
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

    # 3. SAVE PHASE: Guaranteed to run
    print(f"📂 Saving summary to: {md_path}")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(output)
    
    print(f"📂 Saving JSON to: {json_path}")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(winners_list, f, indent=4)
            
    print(f"✅ Success: Files written to {workspace}")

if __name__ == "__main__":
    fetch_and_rank()
