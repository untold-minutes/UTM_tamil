import os
import glob
import pandas as pd
import requests
import sys

def create_poll_request(repo_id, cat_id, title, options, base_headers):
    # Use a simpler mutation structure to ensure compatibility
    mutation = """
    mutation CreatePoll($repoId: ID!, $catId: ID!, $title: String!, $body: String!, $options: [String!]!) {
      createDiscussion(input: {
        repositoryId: $repoId,
        categoryId: $catId,
        title: $title,
        body: $body,
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
    
    headers = base_headers.copy()
    # The Beta header is strictly required for the 'poll' field to exist in the schema
    headers["GraphQL-Features"] = "discussions_polls"

    variables = {
        "repoId": repo_id,
        "catId": cat_id,
        "title": title,
        "body": "Automated poll for upcoming Tamil historical/mythological content.",
        "options": options
    }
    
    response = requests.post(
        "https://api.github.com/graphql", 
        json={"query": mutation, "variables": variables}, 
        headers=headers
    )
    return response.json()

def create_poll():
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        print("Error: No CSV found.")
        sys.exit(1)
    
    latest_file = max(files, key=os.path.getmtime)
    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()
    all_titles = df['TITLE'].dropna().astype(str).tolist()
    
    poll1 = all_titles[:8]
    poll2 = all_titles[8:16]

    token = os.getenv("GH_TOKEN")
    base_headers = {"Authorization": f"Bearer {token}"}
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")

    # Get IDs and check category formats
    query_ids = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(first: 10) {
          nodes { id name }
        }
      }
    }
    """
    id_resp = requests.post("https://api.github.com/graphql", 
                            json={"query": query_ids, "variables": {"owner": owner, "name": repo_name}}, 
                            headers=base_headers).json()

    try:
        repo_id = id_resp['data']['repository']['id']
        categories = id_resp['data']['repository']['discussionCategories']['nodes']
        # Find the category - check if the name matches 'Polls' exactly
        cat_id = next(c['id'] for c in categories if c['name'].lower() == 'polls')
        print(f"Found Category 'Polls' with ID: {cat_id}")
    except (KeyError, StopIteration):
        print(f"Error: Could not find category 'Polls'. Found: {[c['name'] for c in categories]}")
        sys.exit(1)

    # Trigger Polls
    for i, opts in enumerate([poll1, poll2], 1):
        if opts:
            print(f"Sending Poll {i}...")
            result = create_poll_request(repo_id, cat_id, f"Part {i}: {os.path.basename(latest_file)}", opts, base_headers)
            if "errors" in result:
                print(f"Poll {i} Failed: {result['errors']}")
            else:
                print(f"Poll {i} Success: {result['data']['createDiscussion']['discussion']['url']}")

if __name__ == "__main__":
    create_poll()
