import os
import glob
import pandas as pd
import requests
import sys

def create_poll_request(repo_id, cat_id, title, options, base_headers):
    """
    Sends the GraphQL mutation using a single input object.
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
            "body": "Vote for our next content topic! Choose from the options below.",
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

def create_poll():
    # 1. Locate the latest CSV
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        print("Error: No CSV files found.")
        sys.exit(1)
    
    latest_file = max(files, key=os.path.getmtime)
    print(f"Processing File: {latest_file}")

    # 2. Extract Titles and Split
    try:
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        if 'TITLE' not in df.columns:
            print(f"Error: Missing TITLE column.")
            sys.exit(1)

        all_titles = df['TITLE'].dropna().astype(str).tolist()
        poll1_options = all_titles[:8]
        poll2_options = all_titles[8:16]
        
        if not poll1_options:
            print("Error: TITLE column is empty.")
            sys.exit(1)
    except Exception as e:
        print(f"CSV Parse Error: {e}")
        sys.exit(1)

    # 3. API Setup
    token = os.getenv("GH_TOKEN")
    base_headers = {"Authorization": f"Bearer {token}"}
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")

    # 4. Fetch the IDs (Fixed Triple-Quote Syntax)
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
        headers=base_headers
    ).json()

    try:
        repo_id = id_resp['data']['repository']['id']
        categories = id_resp['data']['repository']['discussionCategories']['nodes']
        cat_id = next(c['id'] for c in categories if c['name'].lower() == 'polls')
        print(f"Targeting Category 'Polls' (ID: {cat_id})")
    except (KeyError, StopIteration, TypeError):
        print(f"Error: Could not resolve IDs. API Response: {id_resp}")
        sys.exit(1)

    # 5. Execute Polls
    for i, opts in enumerate([poll1_options, poll2_options], 1):
        if opts:
            print(f"Sending Poll {i}...")
            res = create_poll_request(repo_id, cat_id, f"Part {i}: {os.path.basename(latest_file)}", opts, base_headers)
            if "errors" in res:
                print(f"Poll {i} Failed: {res['errors']}")
            else:
                print(f"Poll {i} Success: {res['data']['createDiscussion']['discussion']['url']}")

if __name__ == "__main__":
    create_poll()
