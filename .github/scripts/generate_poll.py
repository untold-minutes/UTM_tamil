import os
import glob
import pandas as pd
import requests

def create_poll():
    # 1. Find the newest CSV in the planning folder
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        print("Error: No CSV files found in src/01_Planning/")
        return
    
    # Sort by filename or creation time to get the latest week
    latest_file = max(files, key=os.path.getctime)
    print(f"Targeting File: {latest_file}")

    # 2. Parse CSV using your headers: ID, TYPE, TITLE, DESCRIPTION
    try:
        df = pd.read_csv(latest_file)
        # We use the 'TITLE' column for the poll options
        options = df['TITLE'].dropna().astype(str).tolist()[:8] 
        
        if not options:
            print("Error: TITLE column is empty.")
            return
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    # 3. Setup GraphQL Connection
    token = os.getenv("GH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Fetch Repository and Category IDs
    info_query = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 10) {
          nodes { id name }
        }
      }
    }
    """
    vars = {"owner": os.getenv("REPO_OWNER"), "name": os.getenv("REPO_NAME")}
    
    try:
        repo_info = requests.post("https://api.github.com/graphql", json={"query": info_query, "variables": vars}, headers=headers).json()
        repo_id = repo_info['data']['repository']['id']
        
        # Look for the 'Polls' category ID
        categories = repo_info['data']['repository']['discussionCategories']['nodes']
        cat_id = next(c['id'] for c in categories if c['name'] == 'Polls')
    except (KeyError, StopIteration):
        print("Error: Could not find Repository ID or 'Polls' category. Ensure Discussions are enabled.")
        return

    # 4. Create the Discussion Poll
    poll_mutation = """
    mutation($repoId: ID!, $catId: ID!, $title: String!, $body: String!, $options: [String!]!) {
      createDiscussion(input: {
        repositoryId: $repoId, 
        categoryId: $catId,
        title: $title, 
        body: $body,
        poll: { question: "Which content should we produce?", options: $options }
      }) { discussion { url } }
    }
    """
    
    poll_vars = {
        "repoId": repo_id,
        "catId": cat_id,
        "title": f"Content Selection: {os.path.basename(latest_file)}",
        "body": "Please vote for the next video topic based on the planning document.",
        "options": options
    }
    
    result = requests.post("https://api.github.com/graphql", json={"query": poll_mutation, "variables": poll_vars}, headers=headers)
    print(f"Success! Poll created at: {result.json()['data']['createDiscussion']['discussion']['url']}")

if __name__ == "__main__":
    create_poll()
