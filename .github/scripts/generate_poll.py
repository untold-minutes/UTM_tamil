import os
import glob
import pandas as pd
import requests

def create_poll():
    # 1. Dynamically find the newest CSV in the planning folder
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files:
        print("No CSV files found in src/01_Planning/")
        return
    
    latest_file = max(files, key=os.path.getctime)
    print(f"Reading content from: {latest_file}")

    # 2. Parse CSV
    df = pd.read_csv(latest_file)
    options = df['one_liner'].tolist()[:8]

    # 3. Setup GraphQL (Replace these with your actual IDs or fetch them via API)
    # Pro-tip: You can fetch REPO_ID dynamically too
    token = os.getenv("GH_TOKEN")
    headers = {"Authorization": f"Bearer {token}"}
    
    # Example Query to get REPO_ID and CATEGORY_ID
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
    repo_info = requests.post("https://api.github.com/graphql", json={"query": info_query, "variables": vars}, headers=headers).json()
    
    repo_id = repo_info['data']['repository']['id']
    # Find the ID for the category named 'Polls'
    cat_id = next(c['id'] for c in repo_info['data']['repository']['discussionCategories']['nodes'] if c['name'] == 'Polls')

    # 4. Create the Poll
    poll_mutation = """
    mutation($repoId: ID!, $catId: ID!, $title: String!, $options: [String!]!) {
      createDiscussion(input: {
        repositoryId: $repoId, categoryId: $catId,
        title: $title, body: "Vote for this week's content!",
        poll: { question: "Which topic should we cover?", options: $options }
      }) { discussion { url } }
    }
    """
    
    poll_vars = {
        "repoId": repo_id,
        "catId": cat_id,
        "title": f"Content Poll: {os.path.basename(latest_file)}",
        "options": options
    }
    
    result = requests.post("https://api.github.com/graphql", json={"query": poll_mutation, "variables": poll_vars}, headers=headers)
    print(f"Poll created: {result.json()}")

if _name_ == "_main_":
    create_poll()
