import os
import glob
import pandas as pd
import requests
import sys

def create_poll_request(repo_id, cat_id, title, options, headers):
    """
    Sends the GraphQL mutation to GitHub. 
    The 'poll' object must be nested inside the 'input' object.
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
    variables = {
        "repoId": repo_id,
        "catId": cat_id,
        "title": title,
        "options": options
    }
    
    response = requests.post(
        "https://api.github.com/graphql", 
        json={"query": mutation, "variables": variables}, 
        headers=headers
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
        poll2_options = all_titles[8:16] # Handles items 9 through 16
        
        if not poll1_options:
            print("Error: No titles found in CSV.")
            sys.exit(1)

    except Exception as e:
        print(f"CSV Read Error: {e}")
        sys.exit(1)

    # 3. Setup API
    token = os.getenv("GH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
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
        headers=headers
    ).json()

    try:
        repo_id = id_resp['data']['repository']['id']
        categories = id_resp['data']['repository']['discussionCategories']['nodes']
        # Find category named 'Polls' (case-insensitive)
        cat_id = next(c['id'] for c in categories if c['name'].lower() == 'polls')
    except (KeyError, StopIteration):
        print("Error: Could not find 'Polls' category. Check repo settings.")
        sys.exit(1)

    # 5. Execute Poll 1
    print(f"Creating Poll 1 with {len(poll1_options)} options...")
    res1 = create_poll_request(repo_id, cat_id, f"Part 1: {os.path.basename(latest_file)}", poll1_options, headers)
    
    if "errors" in res1:
        print(f"Poll 1 failed: {res1['errors']}")
    else:
        print(f"Poll 1 created: {res1['data']['createDiscussion']['discussion']['url']}")

    # 6. Execute Poll 2 (If more than 8 items exist)
    if poll2_options:
        print(f"Creating Poll 2 with {len(poll2_options)} options...")
        res2 = create_poll_request(repo_id, cat_id, f"Part 2: {os.path.basename(latest_file)}", poll2_options, headers)
        
        if "errors" in res2:
            print(f"Poll 2 failed: {res2['errors']}")
        else:
            print(f"Poll 2 created: {res2['data']['createDiscussion']['discussion']['url']}")

if __name__ == "__main__":
    create_poll()
