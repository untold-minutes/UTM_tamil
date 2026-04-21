import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build

def fetch_and_rank():
    # 1. Setup Google API
    creds_json = json.loads(os.environ['GOOGLE_SERVICE_ACCOUNT'])
    creds = service_account.Credentials.from_service_account_info(creds_json)
    service = build('forms', 'v1', credentials=creds)

    form_id = os.environ['FORM_ID']
    poll_type = os.environ['POLL_TYPE'] # 'Shorts' or 'Long Video'
    
    # 2. Get Responses
    result = service.forms().responses().list(formId=form_id).execute()
    responses = result.get('responses', [])

    vote_counts = {}
    for resp in responses:
        answers = resp.get('answers', {})
        for q_id in answers:
            # Checkbox answers are returned as a list of strings
            choices = answers[q_id].get('textAnswers', {}).get('answers', [])
            for choice in choices:
                val = choice.get('value')
                vote_counts[val] = vote_counts.get(val, 0) + 1

    # 3. Sort and Filter
    sorted_votes = sorted(vote_counts.items(), key=lambda x: x[1], reverse=True)
    
    # Set limits: Top 7 for Shorts, Top 2 for Videos
    limit = 7 if "Shorts" in poll_type else 2
    winners = sorted_votes[:limit]

    # 4. Generate Markdown Output
    print(f"## 🏆 Winners for {poll_type}")
    print(f"The community has spoken! Here are the top picks to move into production:\n")
    
    for i, (title, count) in enumerate(winners, 1):
        print(f"{i}. **{title}** — ({count} votes) ✅")
    
    print(f"\n---\n*Results generated automatically 24h after poll launch.*")

if __name__ == "__main__":
    fetch_and_rank()
