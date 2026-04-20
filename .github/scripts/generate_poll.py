import os
import glob
import pandas as pd
import requests
import sys

def create_poll_request(repo_id, cat_id, title, options, base_headers):
    mutation = """
    mutation CreatePoll($input: CreateDiscussionInput!) {
      createDiscussion(input: $input) {
        discussion { url }
      }
    }
    """
    request_headers = base_headers.copy()
    request_headers.update({
        "GraphQL-Features": "discussions_polls",
        "Accept": "application/vnd.github.v4.idl"
    })

    variables = {
        "input": {
            "repositoryId": repo_id,
            "categoryId": cat_id,
            "title": title,
            "body": "Automatically generated poll for Untold Minutes Tamil.",
            "poll": {
                "question": "Which topic should we cover next?",
                "options": options
            }
        }
    }
    
    response = requests.post("https://api.github.com/graphql", json={"query": mutation, "variables": variables}, headers=request_headers)
    return response.json()

def clean_titles(titles):
    """Trims titles to 80 chars and removes fancy quotes to avoid API errors."""
    cleaned = []
    for t in titles:
        t = str(t).replace('“', '').replace('”', '').replace('—', '-')
        if len(t) > 80:
            t = t[:77] + "..."
        cleaned.append(t.strip())
    return cleaned

def create_poll():
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        sys.exit(1)
    
    latest_file = max(files, key=os.path.getmtime)
    print(f"Processing: {latest_file}")

    # 1. Parse CSV
    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()
    
    # 2. Filter by TYPE (Case-insensitive)
    df['TYPE'] = df['TYPE'].str.strip().str.upper()
    s_rows = df[df['TYPE'] == 'S']['TITLE'].dropna().tolist()
    v_rows = df[df['TYPE'] == 'V']['TITLE'].dropna().tolist()

    # 3. Setup API
    token = os.getenv("GH_TOKEN")
    base_headers = {"Authorization": f"Bearer {token}"}
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")

    query_ids = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 20) { nodes { id name } }
      }
    }
    """
    id_resp = requests.post("https://api.github.com/graphql", json={"query": query_ids, "variables": {"owner": owner, "name": repo_name}}, headers=base_headers).json()
    
    repo_id = id_resp['data']['repository']['id']
    cat_id = next(c['id'] for c in id_resp['data']['repository']['discussionCategories']['nodes'] if c['name'].lower() == 'polls')

    # 4. Process TYPE 'V' (Video) - Max 8
    if v_rows:
        v_cleaned = clean_titles(v_rows[:8])
        print(f"Creating Video Poll (Type V)...")
        res = create_poll_request(repo_id, cat_id, f"Video Poll: {os.path.basename(latest_file)}", v_cleaned, base_headers)
        print(f"V Poll Result: {res.get('data', res.get('errors'))}")

    # 5. Process TYPE 'S' (Stories) - Multiple Polls if needed
    s_cleaned = clean_titles(s_rows)
    # Split list into chunks of 8
    for i in range(0, len(s_cleaned), 8):
        chunk = s_cleaned[i:i + 8]
        poll_num = (i // 8) + 1
        print(f"Creating Story Poll {poll_num} (Type S)...")
        res = create_poll_request(repo_id, cat_id, f"Story Poll Part {poll_num}: {os.path.basename(latest_file)}", chunk, base_headers)
        print(f"S Poll {poll_num} Result: {res.get('data', res.get('errors'))}")

if __name__ == "__main__":
    create_poll()
