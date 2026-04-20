import os
import glob
import pandas as pd
import requests
import json
import sys

def create_poll_request(repo_id, cat_id, title, options, token):
    """
    Creates a discussion with a poll in a single request using 
    Preview headers to unlock the 'poll' field in the GraphQL schema.
    """
    base_url = "https://api.github.com/graphql"
    
    # These headers tell GitHub to use the 'Preview' schema where polls exist.
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v4.idl, application/vnd.github.merge-info-preview+json",
        "GraphQL-Features": "discussions_polls"
    }

    mutation = """
    mutation($input: CreateDiscussionInput!) {
      createDiscussion(input: $input) {
        discussion {
          url
        }
      }
    }
    """
    
    variables = {
        "input": {
            "repositoryId": repo_id,
            "categoryId": cat_id,
            "title": title,
            "body": "Daily content selection poll for **Untold Minutes Tamil**. Help us choose the next topic by voting below!",
            "poll": {
                "question": "Which topic should we cover next?",
                "options": options
            }
        }
    }
    
    response = requests.post(
        base_url, 
        json={"query": mutation, "variables": variables}, 
        headers=headers
    )
    return response.json()

def clean_titles(titles):
    """Sanitizes Tamil text and limits length for GitHub API compatibility."""
    cleaned = []
    for t in titles:
        # Standardize punctuation and quotes
        t = str(t).replace('“', '').replace('”', '').replace('—', '-').replace('"', "'").replace('…', '...')
        # GitHub poll options are limited (80 characters is the safe zone)
        if len(t) > 80:
            t = t[:77] + "..."
        cleaned.append(t.strip())
    return cleaned

def create_poll():
    # 1. Locate Latest CSV
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        print("No CSV files found in src/01_Planning/")
        sys.exit(0)
    
    latest_file = max(files, key=os.path.getmtime)
    print(f"Processing File: {latest_file}")

    # 2. Parse CSV
    try:
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
    except Exception as e:
        print(f"CSV Parse Error: {e}")
        sys.exit(1)
    
    if 'TYPE' not in df.columns or 'TITLE' not in df.columns:
        print("Error: CSV must contain 'TYPE' and 'TITLE' columns.")
        sys.exit(1)

    # Filter by TYPE
    df['TYPE'] = df['TYPE'].str.strip().str.upper()
    s_rows = df[df['TYPE'] == 'S']['TITLE'].dropna().tolist()
    v_rows = df[df['TYPE'] == 'V']['TITLE'].dropna().tolist()

    # 3. API Environment
    token = os.getenv("GH_TOKEN")
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")
    
    if not token:
        print("Error: GH_TOKEN is not set.")
        sys.exit(1)

    # 4. Resolve Repo and Category IDs
    query_ids = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 20) {
          nodes { id name }
        }
      }
    }
    """
    id_resp = requests.post(
        "https://api.github.com/graphql", 
        json={"query": query_ids, "variables": {"owner": owner, "name": repo_name}}, 
        headers={"Authorization": f"Bearer {token}"}
    ).json()

    try:
        repo_id = id_resp['data']['repository']['id']
        categories = id_resp['data']['repository']['discussionCategories']['nodes']
        cat_id = next(c['id'] for c in categories if c['name'].lower() == 'polls')
        print(f"IDs Resolved. Target Category: Polls.")
    except (KeyError, StopIteration, TypeError):
        print(f"ID Resolution Error: {id_resp}")
        sys.exit(1)

    # 5. Process Video (V) Poll
    if v_rows:
        v_cleaned = clean_titles(v_rows[:8])
        print("Creating Video Poll...")
        res = create_poll_request(repo_id, cat_id, f"Video Poll: {os.path.basename(latest_file)}", v_cleaned, token)
        if 'errors' in res:
            print(f"Video Poll Failed: {res['errors']}")
        else:
            print(f"Video Poll Success: {res['data']['createDiscussion']['discussion']['url']}")

    # 6. Process Story (S) Polls
    s_cleaned = clean_titles(s_rows)
    for i in range(0, len(s_cleaned), 8):
        chunk = s_cleaned[i:i+8]
        p_num = (i // 8) + 1
        print(f"Creating Story Poll {p_num}...")
        res = create_poll_request(repo_id, cat_id, f"Story Poll {p_num}: {os.path.basename(latest_file)}", chunk, token)
        if 'errors' in res:
            print(f"Story Poll {p_num} Failed: {res['errors']}")
        else:
            print(f"Story Poll {p_num} Success: {res['data']['createDiscussion']['discussion']['url']}")

if __name__ == "__main__":
    create_poll()
