import os
import glob
import pandas as pd
import requests
import sys

def create_poll_request(repo_id, cat_id, title, options, headers):
    """Helper function to send the GraphQL mutation"""
    mutation = """
    mutation($repoId: ID!, $catId: ID!, $title: String!, $options: [String!]!) {
      createDiscussion(input: {
        repositoryId: $repoId,
        categoryId: $catId,
        title: $title,
        body: "Automated content selection poll.",
        poll: { question: "Which topic should we cover?", options: $options }
      }) { discussion { url } }
    }
    """
    vars = {"repoId": repo_id, "catId": cat_id, "title": title, "options": options}
    return requests.post("https://api.github.com/graphql", json={"query": mutation, "variables": vars}, headers=headers).json()

def create_poll():
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        sys.exit(1)
    
    latest_file = max(files, key=os.path.getmtime)
    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()
    
    all_options = df['TITLE'].dropna().astype(str).tolist()
    
    # --- Split Logic ---
    # Poll 1: Items 1-8 | Poll 2: Items 9-15
    poll1_options = all_options[:8]
    poll2_options = all_options[8:16] # GitHub max is 8, so we take up to 16 total

    # Setup API
    token = os.getenv("GH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")

    # Get IDs
    query_ids = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 10) { nodes { id name } }
      }
    }
    """
    id_resp = requests.post("https://api.github.com/graphql", json={"query": query_ids, "variables": {"owner": owner, "name": repo_name}}, headers=headers).json()
    
    repo_id = id_resp['data']['repository']['id']
    cat_id = next(c['id'] for c in id_resp['data']['repository']['discussionCategories']['nodes'] if c['name'].lower() == 'polls')

    # Create Poll 1
    res1 = create_poll_request(repo_id, cat_id, f"Part 1: {os.path.basename(latest_file)}", poll1_options, headers)
    if "errors" in res1:
        print(f"Poll 1 Error: {res1['errors']}")
    else:
        print(f"Poll 1 created: {res1['data']['createDiscussion']['discussion']['url']}")

    # Create Poll 2 (Only if there are more than 8 items)
    if poll2_options:
        res2 = create_poll_request(repo_id, cat_id, f"Part 2: {os.path.basename(latest_file)}", poll2_options, headers)
        if "errors" in res2:
            print(f"Poll 2 Error: {res2['errors']}")
        else:
            print(f"Poll 2 created: {res2['data']['createDiscussion']['discussion']['url']}")

if __name__ == "__main__":
    create_poll()
