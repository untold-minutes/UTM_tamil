import os
import json
import sys

def fetch_and_rank():
    # 1. SETUP PATHS
    workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
    json_path = os.path.join(workspace, "latest_winners.json")
    md_path = os.path.join(workspace, "winner_summary.md")
    
    winners_list = []
    output = "## 📊 Poll Results\n"

    # Force immediate output to GitHub Logs
    print("🚀 SCRIPT STARTING", flush=True)

    try:
        from googleapiclient.discovery import build
        from google.oauth2 import service_account
        
        creds_raw = os.environ.get('GOOGLE_SERVICE_ACCOUNT')
        form_id = os.environ.get('FORM_ID')
        poll_type = os.environ.get('POLL_TYPE', 'Shorts')

        if not creds_raw:
            print("❌ ERROR: GOOGLE_SERVICE_ACCOUNT is empty", flush=True)
            return

        # 2. GOOGLE API LOGIC
        print(f"📡 Connecting to Form: {form_id}", flush=True)
        creds_dict = json.loads(creds_raw)
        creds = service_account.Credentials.from_service_account_info(
            creds_dict, scopes=['https://www.googleapis.com/auth/forms.responses.readonly']
        )
        service = build('forms', 'v1', credentials=creds)

        result = service.forms().responses().list(formId=form_id).execute()
        responses = result.get('responses', [])
        type_code = "V" if "Long" in poll_type else "S"
        
        if not responses:
            print("⚠️ No responses found in Form.", flush=True)
            output += "⚠️ No votes found in the form."
        else:
            votes = {}
            for resp in responses:
                answers = resp.get('answers', {})
                for ans_id, content in answers.items():
                    text_list = content.get('textAnswers', {}).get('answers', [])
                    for t in text_list:
                        val = t.get('value')
                        if val:
                            votes[str(val)] = votes.get(str(val), 0) + 1

            sorted_votes = sorted(votes.items(), key=lambda x: x[1], reverse=True)
            limit = 2 if type_code == "V" else 5
            
            for i, (title, count) in enumerate(sorted_votes[:limit], 1):
                output += f"{i}. **{title}** — ({count} votes) ✅\n"
                winners_list.append({
                    "type": str(type_code),
                    "title": str(title),
                    "rank": int(i)
                })
        
        output += "\n---\nTally successful."
        print(f"✅ Tally complete. Found {len(winners_list)} winners.", flush=True)

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}", flush=True)
        output += f"\n\n❌ ERROR: {str(e)}"

    # 3. THE SAVE PHASE
    # We write the JSON file first.
    print(f"💾 Attempting to write JSON to: {json_path}", flush=True)
    try:
        with open(json_path, "w", encoding="utf-8") as f:
            # We use a very safe dump configuration for international characters
            json_string = json.dumps(winners_list, indent=4, ensure_ascii=False)
            f.write(json_string)
        print("🎉 JSON WRITE SUCCESSFUL", flush=True)
    except Exception as je:
        print(f"❌ JSON WRITE FAILED: {str(je)}", flush=True)

    print(f"💾 Attempting to write MD to: {md_path}", flush=True)
    try:
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(output)
        print("🎉 MD WRITE SUCCESSFUL", flush=True)
    except Exception as me:
        print(f"❌ MD WRITE FAILED: {str(me)}", flush=True)

    print("🏁 SCRIPT REACHED END", flush=True)

if __name__ == "__main__":
    fetch_and_rank()
