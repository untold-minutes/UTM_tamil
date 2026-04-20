import os
import glob
import pandas as pd
import requests
import sys

def create_poll_request(repo_id, cat_id, title, options, base_headers):
    """
    Sends the GraphQL mutation using a single input object.
    This is the most compatible way to trigger GitHub Polls via API.
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
    
    # We must explicitly use the preview header to unlock the 'poll' field
    request_headers = base_headers.copy()
    request_headers.update({
        "GraphQL-Features": "discussions_polls",
        "Accept": "application/vnd.github.v4.idl"
    })

    # Packaging all variables into the 'input' object as required by the schema
    variables = {
        "input": {
            "repositoryId": repo_id,
            "categoryId": cat_id,
            "title": title,
            "body": "New content selection poll! Please vote for the topic you want to see next.",
            "poll": {
                "question": "Which topic should we cover?",
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
        print("Error: No CSV files found in src/01_Planning/")
        sys.exit(1)
    
    latest_file = max(files, key=os.path.getmtime)
    print(f"Processing File: {latest_file}")

    # 2. Extract Titles and Split into Two Polls
    try:
        df = pd.read_csv(latest_file)
        df.columns = df.columns.str.strip().str.upper()
        
        if 'TITLE' not in df.columns:
            print(f"Error: Missing TITLE column. Available: {list(df.columns)}")
            sys.exit(1)

        all_titles = df['TITLE'].dropna().astype(str).tolist()
        
        # GitHub max is 8 per poll. 
        # For 15 items, we split into 8 and 7.
        poll1_options = all_titles[:8]
        poll2_options = all_titles[8:16]
        
        if not poll1_options:
            print("Error: The TITLE column in the CSV is empty.")
            sys.exit(1)

    except Exception as e:
        print(f"CSV Parse Error: {e}")
        sys.exit(1)

    # 3. Authorization and Metadata
    token = os.getenv("GH_TOKEN")
    if not token:
        print("Error: GH_TOKEN environment variable is missing.")
        sys.exit(1)

    base_headers = {"Authorization": f"Bearer {token}"}
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")

    # 4. Fetch the Repo and Category IDs
    query_ids = """
    query($owner: String!, $name: String!) {
      repository(owner: $owner, name: $name) {
        id
        discussionCategories(
