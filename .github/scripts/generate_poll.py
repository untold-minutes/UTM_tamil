import os
import glob
import pandas as pd
import requests
import json
import sys

def create_poll_request(repo_id, cat_id, title, options, token):
    """
    Sends the GraphQL mutation using the IDL Accept header.
    Mimics the internal GitHub web environment to force 'poll' visibility.
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
        t = str(t).replace('“', '').replace('”', '').replace('—', '-').replace('"', "'").replace('…', '...')
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

    # 2. Parse CSV
    try:
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
    except Exception as e:
        print(f"CSV Parse Error: {e}")
        sys.exit(1)
    
    if 'TYPE' not in df.columns or 'TITLE' not in df.columns:
        print("Error: Missing TYPE or TITLE column.")
        sys.exit(1)

    df['TYPE'] = df['TYPE'].str.strip().str.upper()
    s_rows = df[df['TYPE'] == 'S']['TITLE'].dropna().tolist()
    v_rows = df[df['TYPE'] == 'V']['TITLE'].dropna().tolist()

    # 3. Environment Setup
    token = os.getenv("GH_TOKEN")
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")
    
    if not token:
        print("Error: GH_TOKEN is missing.")
        sys.exit(1)

    # Fetch IDs
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
        print(f"Verified Repo ID: {repo_id} | Category ID: {cat_id}")
    except (KeyError, StopIteration, TypeError):
        print(f"Critical Error: Could not resolve IDs. Response: {id_resp}")
        sys.exit(1)

    # 4. Video (V) Poll
    if v_rows:
        v_cleaned = clean_titles(v_rows[:8])
        print("Creating Video Poll...")
        res_v = create_poll_request(repo_id, cat_id, f"Video Poll: {os.path.basename(latest_file)}", v_cleaned, token)
        if 'errors' in res_v:
            print(f"V Poll Failed: {res_v['errors']}")
        else:
            print(f"V Poll Success: {res_v['data']['createDiscussion']['discussion']['url']}")

    # 5. Story (S) Polls
    s_cleaned = clean_titles(s_rows)
    for i in range(0, len(s_cleaned), 8):
        chunk = s_cleaned[i:i + 8]
        p_num = (i // 8) + 1
        print(f"Creating Story Poll {p_num}...")
        res_s = create_poll_request(repo_id, cat_id, f"Story Poll Part {p_num}: {os.path.basename(latest_file)}", chunk, token)
        if 'errors' in res_s:
            print(f"S Poll {p_num} Failed: {res_s['errors']}")
        else:
            print(f"S Poll {p_num} Success: {res_s['data']['createDiscussion']['discussion']['url']}")

if __name__ == "__main__":
    create_poll()
