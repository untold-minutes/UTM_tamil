import os
import glob
import pandas as pd
import requests
import json
import sys

def create_poll_request(repo_id, cat_id, title, options, token):
    """
    Sends the GraphQL mutation using the IDL Accept header.
    This mimics the internal GitHub web environment to force 'poll' visibility.
    """
    mutation = """
    mutation CreatePoll($input: CreateDiscussionInput!) {
      createDiscussion(input: $input) {
        discussion {
          url
        }
      }
    }
    """
    
    # These headers are the "Golden Ticket" for preview features
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v4.idl",
        "GraphQL-Features": "discussions_polls"
    }

    variables = {
        "input": {
            "repositoryId": repo_id,
            "categoryId": cat_id,
            "title": title,
            "body": "Daily content selection poll for Untold Minutes Tamil.",
            "poll": {
                "question": "Which topic should we cover next?",
                "options": options
            }
        }
    }
    
    payload = {
        "query": mutation,
        "variables": variables
    }
    
    response = requests.post(
        "https://api.github.com/graphql", 
        data=json.dumps(payload), 
        headers=headers
    )
    return response.json()

def clean_titles(titles):
    """Trims and sanitizes titles for GitHub's character limits."""
    cleaned = []
    for t in titles:
        # Strip fancy quotes and emojis that can cause encoding rejection
        t = str(t).replace('“', '').replace('”', '').replace('—', '-').replace('"', "'").replace('…', '...')
        # Limit to 80 characters for safety
        if len(t) > 80:
            t = t[:77] + "..."
        cleaned.append(t.strip())
    return cleaned

def create_poll():
    # 1. Find the newest Planning CSV
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        print("Error: No CSV files found.")
        sys.exit(0)
    
    latest_file = max(files, key=os.path.getmtime)
    print(f"Processing: {latest_file}")

    # 2. Parse CSV and filter by TYPE
    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()
    
    if 'TYPE' not in df.columns or 'TITLE' not in df.columns:
        print("Error: Missing TYPE or TITLE column.")
        sys.exit(1)

    df['TYPE'] = df['TYPE'].str.strip().str.upper()
    s_rows = df[df['TYPE'] == 'S']['TITLE'].dropna().tolist()
    v_rows = df[df['TYPE'] == 'V']['TITLE'].dropna().tolist()

    # 3. Environment Setup
    token = os.
