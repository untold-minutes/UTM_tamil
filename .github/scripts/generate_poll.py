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
    # Adding every possible preview header to ensure the 'poll' field is visible
    request_headers.update({
        "GraphQL-Features": "discussions_polls",
        "Accept": "application/vnd.github.v4.idl, application/vnd.github.merge-info-preview+json, application/json"
    })

    variables = {
        "input": {
            "repositoryId": repo_id,
            "categoryId": cat_id,
            "title": title,
            "body": "Daily content poll for Untold Minutes Tamil. Cast your vote below!",
            "poll": {
                "question": "Which topic should we cover next?",
                "options": options
            }
        }
    }
    
    response = requests.post("https://api.github.com/graphql", json={"query": mutation, "variables": variables}, headers=request_headers)
    return response.json()

def clean_titles(titles):
    cleaned = []
    for t in titles:
        # Strict cleaning for Tamil characters and special punctuation
        t = str(t).replace('“', '').replace('”', '').replace('—', '-').replace('"', "'").replace('…', '...')
        if len(t) > 80:
            t = t[:77] + "..."
        cleaned.append(t.strip())
    return cleaned

def create_poll():
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        sys.exit(0)
    
    latest_file = max(files, key=os.path.getmtime)
    print(f"Processing File: {latest_file}")

    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()
    
    if 'TYPE' not in df.columns or 'TITLE' not in df.columns:
        print("CSV Error: Need TYPE and TITLE columns.")
        sys.exit(1)

    df['TYPE'] = df['TYPE'].str.strip().str.upper()
    s_rows = df[df['TYPE'] == 'S']['TITLE'].dropna().tolist()
    v_rows = df[df['TYPE'] == 'V']['TITLE'].dropna().tolist()

    token = os.getenv("GH_TOKEN")
    base_headers = {"Authorization": f"Bearer {token}"}
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")

    # Fetch IDs
    query_ids = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 20) { nodes { id name } }
      }
    }
    """
    id_resp = requests.post("https://api.github.com/graphql", json={"query": query_ids, "variables": {"owner": owner, "name": repo_name}}, headers=base_headers).json()
    
    try:
        repo_id = id_resp['data']['repository']['id']
        # Double check the name matches exactly
        cat_id = next(c['id'] for c in id_resp['data']['repository']['discussionCategories']['nodes'] if c['name'].lower() == 'polls')
        print(f"Successfully matched 'Polls' category. ID: {cat_id}")
    except (KeyError, StopIteration):
        print("Error: Category 'Polls' not found. Please recreate it in Settings.")
        sys.exit(1)

    # Process Video (V)
    if v_rows:
        v_cleaned = clean_titles(v_rows[:8])
        print("Triggering Video Poll...")
        res = create_poll_request(repo_id, cat_id, f"Video Poll: {os.path.basename(latest_file)}", v_cleaned, base_headers)
        print(f"V Result: {'Success' if 'data' in res else res.get('errors')}")

    # Process Stories (S)
    s_cleaned = clean_titles(s_rows)
    for i in range(0, len(s_cleaned), 8):
        chunk = s_cleaned[i:i + 8]
        p_num = (i // 8) + 1
        print(f"Triggering Story Poll {p_num}...")
        res = create_poll_request(repo_id, cat_id, f"Story Poll Part {p_num}: {os.path.basename(latest_file)}", chunk, base_headers)
        print(f"S{p_num} Result: {'Success' if 'data' in res else res.get('errors')}")

if __name__ == "__main__":
    create_poll()
