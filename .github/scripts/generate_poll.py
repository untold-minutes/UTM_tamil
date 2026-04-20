import os
import glob
import pandas as pd
import requests
import json
import sys

def create_poll_flow(repo_id, cat_id, title, options, token):
    """
    Two-step process to bypass API schema limitations:
    1. Create a standard Discussion.
    2. Add a Poll to that Discussion using the specific Poll mutation.
    """
    base_url = "https://api.github.com/graphql"
    
    # Standard headers for discussion creation
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v4.idl"
    }

    # --- STEP 1: Create the Discussion ---
    create_disc_mutation = """
    mutation($input: CreateDiscussionInput!) {
      createDiscussion(input: $input) {
        discussion { id url }
      }
    }
    """
    
    disc_vars = {
        "input": {
            "repositoryId": repo_id,
            "categoryId": cat_id,
            "title": title,
            "body": "Daily content selection poll for **Untold Minutes Tamil**. Please cast your vote below to help us choose the next topic!"
        }
    }
    
    resp = requests.post(base_url, json={"query": create_disc_mutation, "variables": disc_vars}, headers=headers).json()
    
    if "errors" in resp:
        return f"Step 1 (Discussion Creation) Failed: {resp['errors']}"
    
    discussion_id = resp['data']['createDiscussion']['discussion']['id']
    discussion_url = resp['data']['createDiscussion']['discussion']['url']

    # --- STEP 2: Add the Poll to the created Discussion ---
    add_poll_mutation = """
    mutation($input: AddDiscussionPollInput!) {
      addDiscussionPoll(input: $input) {
        poll { id }
      }
    }
    """
    
    poll_vars = {
        "input": {
            "discussionId": discussion_id,
            "question": "Which topic should we cover next?",
            "options": options
        }
    }
    
    # Add the specific feature flag for polls
    poll_headers = headers.copy()
    poll_headers["GraphQL-Features"] = "discussions_polls"
    
    poll_resp = requests.post(base_url, json={"query": add_poll_mutation, "variables": poll_vars}, headers=poll_headers).json()
    
    if "errors" in poll_resp:
        return f"Discussion created at {discussion_url}, but Step 2 (Poll Addition) failed: {poll_resp['errors']}"
    
    return f"Success! Poll live at: {discussion_url}"

def clean_titles(titles):
    """Sanitizes Tamil text and limits length for GitHub API compatibility."""
    cleaned = []
    for t in titles:
        # Standardize punctuation and quotes
        t = str(t).replace('“', '').replace('”', '').replace('—', '-').replace('"', "'").replace('…', '...')
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
        print("Error: GH_TOKEN is not set in environment.")
        sys.exit(1)

    # 4. Resolve IDs
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
        print(f"Connected to Repo. Target Category 'Polls' identified.")
    except (KeyError, StopIteration, TypeError):
        print(f"ID Resolution Error. Response: {id_resp}")
        sys.exit(1)

    # 5. Process Video (V) Polls
    if v_rows:
        print("Creating Video Poll...")
        result = create_poll_flow(repo_id, cat_id, f"Video Poll: {os.path.basename(latest_file)}", clean_titles(v_rows[:8]), token)
        print(result)

    # 6. Process Story (S) Polls
    s_cleaned = clean_titles(s_rows)
    for i in range(0, len(s_cleaned), 8):
        chunk = s_cleaned[i:i+8]
        p_num = (i // 8) + 1
        print(f"Creating Story Poll {p_num}...")
        result = create_poll_flow(repo_id, cat_id, f"Story Poll Part {p_num}: {os.path.basename(latest_file)}", chunk, token)
        print(result)

if __name__ == "__main__":
    create_poll()
