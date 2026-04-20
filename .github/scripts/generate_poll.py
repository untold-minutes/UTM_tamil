import os
import glob
import pandas as pd
import requests
import sys

def create_poll_request(repo_id, cat_id, title, options, base_headers):
    """
    Sends the GraphQL mutation with the required Beta header for Polls.
    """
    mutation = """
    mutation($repoId: ID!, $catId: ID!, $title: String!, $options: [String!]!) {
      createDiscussion(input: {
        repositoryId: $repoId,
        categoryId: $catId,
        title: $title,
        body: "Automated content selection poll based on the latest planning CSV.",
        poll: {
          question: "Which topic should we cover next?",
          options: $options
        }
      }) {
        discussion {
          url
        }
      }
    }
    """
    
    # Critical: The 'discussions_polls' feature must be enabled via header
    request_headers = base_headers.copy()
    request_headers.update({
        "GraphQL-Features": "discussions_polls"
    })

    variables = {
        "repoId": repo_id,
        "catId": cat_id,
        "title": title,
        "options": options
    }
    
    response = requests.post(
        "https://api.github.com/graphql", 
        json={"query": mutation, "variables": variables}, 
        headers=request_headers
    )
    return response.json()

def create_poll():
    # 1. Find the newest CSV
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        print("Error: No CSV files found in src/01_Planning/")
        sys.exit(1)
    
    latest_file = max(files, key=os.path.getmtime)
    print(f"Processing File: {latest_file}")

    # 2. Parse CSV and Clean Headers
    try:
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        if 'TITLE' not in df.columns:
            print(f"Error: Missing TITLE column. Found: {list(df.columns)}")
            sys.exit(1)

        all_titles = df['TITLE'].dropna().astype(str).tolist()
        
        # Split into two lists (Max 8 per poll)
        poll1_options = all_titles[:8]
        poll2_options = all_titles[8:16] 
        
        if not poll1_options:
            print("Error: No titles found in CSV.")
            sys.exit(1)

    except Exception as e:
        print(f"CSV Read Error: {e}")
        sys.exit(1)

    # 3. Setup Base API Headers
    token = os.getenv("GH_TOKEN")
    base_headers = {"Authorization": f"Bearer {token}"}
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")

    # 4. Get Repository and Category IDs
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
        # Find category named 'Polls'
        cat_id = next(c['id'] for c in categories if c['name'].lower() == 'polls')
    except (KeyError, StopIteration, TypeError):
        print(f"Error: Could not find 'Polls' category. API Response: {id_resp}")
        sys.exit(1)

    # 5. Execute Poll 1
    print(f"Creating Poll 1 with {len(poll1_options)} options...")
    res1 = create_poll_request(repo_id, cat_id, f"Part 1: {os.path.basename(latest_file)}", poll1_options, base_headers)
    
    if "errors" in res1:
        print(f"Poll 1 failed: {res1['errors']}")
    else:
        print(f"Poll 1 created: {res1['data']['createDiscussion']['discussion']['url']}")

    # 6. Execute Poll 2 (If more than 8 items exist)
    if poll2_options:
        print(f"Creating Poll 2 with {len(poll2_options)} options...")
        res2 = create_poll_request(repo_id, cat_id, f"Part 2: {os.path.basename(latest_file)}", poll2_options, base_headers)
        
        if "errors" in res2:
            print(f"Poll 2 failed: {res2['errors']}")
        else:
            print(f"Poll 2 created: {res2['data']['createDiscussion']['discussion']['url']}")

if __name__ == "__main__":
    create_poll()
