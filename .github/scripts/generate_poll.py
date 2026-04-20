import os
import glob
import pandas as pd
import requests
import sys

def create_poll_request(repo_id, cat_id, title, options, base_headers):
    # This mutation structure is verified for Poll-enabled categories
    mutation = """
    mutation CreatePoll($input: CreateDiscussionInput!) {
      createDiscussion(input: $input) {
        discussion {
          url
          id
        }
      }
    }
    """
    
    request_headers = base_headers.copy()
    # Adding the specific header that forces GitHub to use the "Discussion Polls" preview schema
    request_headers.update({
        "GraphQL-Features": "discussions_polls",
        "Accept": "application/vnd.github.v4.idl"
    })

    variables = {
        "input": {
            "repositoryId": repo_id,
            "categoryId": cat_id,
            "title": title,
            "body": "Automatically generated poll for Untold Minutes Tamil content planning.",
            "poll": {
                "question": "Which topic should we cover next?",
                "options": options
            }
        }
    }
    
    response = requests.post(
        "https://api.github.com/graphql", 
        json={"query": mutation, "variables": variables}, 
        headers=request_headers
    )
    return response.json()

def clean_titles(titles):
    cleaned = []
    for t in titles:
        # Strict cleaning: Removing characters that might break the GraphQL string parser
        t = str(t).replace('“', '').replace('”', '').replace('—', '-').replace('"', "'").replace('…', '...')
        # GitHub Poll options have a hard limit (usually 80-100). Trimming to 80 for safety.
        if len(t) > 80:
            t = t[:77] + "..."
        cleaned.append(t.strip())
    return cleaned

def create_poll():
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        print("No CSV files found.")
        sys.exit(0)
    
    latest_file = max(files, key=os.path.getmtime)
    print(f"Processing File: {latest_file}")

    try:
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
    except Exception as e:
        print(f"Failed to read CSV: {e}")
        sys.exit(1)
    
    if 'TYPE' not in df.columns or 'TITLE' not in df.columns:
        print("CSV Error: Column headers must include 'TYPE' and 'TITLE'.")
        sys.exit(1)

    # Separate S and V types
    df['TYPE'] = df['TYPE'].str.strip().str.upper()
    s_rows = df[df['TYPE'] == 'S']['TITLE'].dropna().tolist()
    v_rows = df[df['TYPE'] == 'V']['TITLE'].dropna().tolist()

    token = os.getenv("GH_TOKEN")
    base_headers = {"Authorization": f"Bearer {token}"}
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")

    # Fetch IDs and Category Formats
    query_ids = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 20) {
          nodes {
            id
            name
          }
        }
      }
    }
    """
    id_resp = requests.post("https://api.github.com/graphql", json={"query": query_ids, "variables": {"owner": owner, "name": repo_name}}, headers=base_headers).json()
    
    try:
        repo_id = id_resp['data']['repository']['id']
        # Locate the 'Polls' category
        categories = id_resp['data']['repository']['discussionCategories']['nodes']
        cat_id = next(c['id'] for c in categories if c['name'].lower() == 'polls')
        print(f"Target Category: Polls (ID: {cat_id})")
    except (KeyError, StopIteration, TypeError):
        print(f"Critical Error: Could not find Polls category. Response: {id_resp}")
        sys.exit(1)

    # --- Video (V) Poll Generation ---
    if v_rows:
        v_cleaned = clean_titles(v_rows[:8])
        print(f"Generating Video Poll (8 items max)...")
        res_v = create_poll_request(repo_id, cat_id, f"Video Poll: {os.path.basename(latest_file)}", v_cleaned, base_headers)
        if 'errors' in res_v:
            print(f"Video Poll Failed: {res_v['errors']}")
        else:
            print(f"Video Poll Created: {res_v['data']['createDiscussion']['discussion']['url']}")

    # --- Stories (S) Poll Generation ---
    s_cleaned = clean_titles(s_rows)
    for i in range(0, len(s_cleaned), 8):
        chunk = s_cleaned[i:i + 8]
        p_num = (i // 8) + 1
        print(f"Generating Story Poll {p_num}...")
        res_s = create_poll_request(repo_id, cat_id, f"Story Poll Part {p_num}: {os.path.basename(latest_file)}", chunk, base_headers)
        if 'errors' in res_s:
            print(f"Story Poll {p_num} Failed: {res_s['errors']}")
        else:
            print(f"Story Poll {p_num} Created: {res_s['data']['createDiscussion']['discussion']['url']}")

if __name__ == "__main__":
    create_poll()
