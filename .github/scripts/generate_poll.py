import os
import glob
import pandas as pd
import requests
import json
import sys

def create_poll_flow(repo_id, cat_id, title, options, token):
    """
    Standard Discussion creation followed by a Direct-Field Poll injection.
    """
    base_url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github.v4.idl",
        "GraphQL-Features": "discussions_polls"
    }

    # STEP 1: Create the Discussion (Standard)
    create_mutation = """
    mutation($repoId: ID!, $catId: ID!, $title: String!, $body: String!) {
      createDiscussion(input: {repositoryId: $repoId, categoryId: $catId, title: $title, body: $body}) {
        discussion { id url }
      }
    }
    """
    
    create_vars = {
        "repoId": repo_id,
        "catId": cat_id,
        "title": title,
        "body": "Vote for the next **Untold Minutes Tamil** topic below!"
    }
    
    resp = requests.post(base_url, json={"query": create_mutation, "variables": create_vars}, headers=headers).json()
    
    if "errors" in resp:
        return f"Failed to create Discussion: {resp['errors']}"
    
    disc_id = resp['data']['createDiscussion']['discussion']['id']
    disc_url = resp['data']['createDiscussion']['discussion']['url']

    # STEP 2: Add Poll using Literal Mutation (Avoiding 'AddDiscussionPollInput' type error)
    # We pass options as a variable but keep the mutation structure flat.
    add_poll_mutation = """
    mutation($discId: ID!, $options: [String!]!) {
      addDiscussionPoll(input: {discussionId: $discId, question: "Which topic should we cover next?", options: $options}) {
        poll { id }
      }
    }
    """
    
    poll_vars = {
        "discId": disc_id,
        "options": options
    }
    
    poll_resp = requests.post(base_url, json={"query": add_poll_mutation, "variables": poll_vars}, headers=headers).json()
    
    if "errors" in poll_resp:
        # Check if it's the 'Field not defined' again
        return f"Discussion created ({disc_url}), but Poll failed: {poll_resp['errors']}"
    
    return f"Success! Poll live at: {disc_url}"

def clean_titles(titles):
    cleaned = []
    for t in titles:
        t = str(t).replace('“', '').replace('”', '').replace('—', '-').replace('"', "'").replace('…', '...')
        if len(t) > 80: t = t[:77] + "..."
        cleaned.append(t.strip())
    return cleaned

def create_poll():
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files: sys.exit(0)
    
    latest_file = max(files, key=os.path.getmtime)
    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()
    
    df['TYPE'] = df['TYPE'].str.strip().str.upper()
    s_rows = df[df['TYPE'] == 'S']['TITLE'].dropna().tolist()
    v_rows = df[df['TYPE'] == 'V']['TITLE'].dropna().tolist()

    token = os.getenv("GH_TOKEN")
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")
    
    # Get IDs
    query_ids = "query($o:String!,$n:String!){repository(owner:$o,name:$n){id discussionCategories(first:20){nodes{id name}}}}"
    id_resp = requests.post(base_url := "https://api.github.com/graphql", json={"query": query_ids, "variables": {"o": owner, "n": repo_name}}, headers={"Authorization": f"Bearer {token}"}).json()
    
    repo_id = id_resp['data']['repository']['id']
    cat_id = next(c['id'] for c in id_resp['data']['repository']['discussionCategories']['nodes'] if c['name'].lower() == 'polls')

    # Process V
    if v_rows:
        print(create_poll_flow(repo_id, cat_id, f"Video Poll: {os.path.basename(latest_file)}", clean_titles(v_rows[:8]), token))

    # Process S
    s_cleaned = clean_titles(s_rows)
    for i in range(0, len(s_cleaned), 8):
        chunk = s_cleaned[i:i+8]
        print(create_poll_flow(repo_id, cat_id, f"Story Poll {(i//8)+1}: {os.path.basename(latest_file)}", chunk, token))

if __name__ == "__main__":
    create_poll()
