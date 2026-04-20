import os
import glob
import pandas as pd
import requests
import json
import sys

def create_poll_flow(repo_id, cat_id, title, options, token):
    """
    Two-step process:
    1. Create the Discussion.
    2. Add the Poll to that Discussion.
    """
    base_url = "https://api.github.com/graphql"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "GraphQL-Features": "discussions_polls"
    }

    # STEP 1: Create the Discussion
    create_disc_mutation = """
    mutation($repoId: ID!, $catId: ID!, $title: String!, $body: String!) {
      createDiscussion(input: {repositoryId: $repoId, categoryId: $catId, title: $title, body: $body}) {
        discussion { id url }
      }
    }
    """
    
    disc_vars = {
        "repoId": repo_id,
        "catId": cat_id,
        "title": title,
        "body": "Vote for the next topic below!"
    }
    
    resp = requests.post(base_url, json={"query": create_disc_mutation, "variables": disc_vars}, headers=headers).json()
    
    if "errors" in resp:
        return f"Failed to create Discussion: {resp['errors']}"
    
    discussion_id = resp['data']['createDiscussion']['discussion']['id']
    discussion_url = resp['data']['createDiscussion']['discussion']['url']

    # STEP 2: Add the Poll to the created Discussion
    add_poll_mutation = """
    mutation($discId: ID!, $question: String!, $options: [String!]!) {
      addDiscussionPoll(input: {discussionId: $discId, question: $question, options: $options}) {
        poll { id }
      }
    }
    """
    
    poll_vars = {
        "discId": discussion_id,
        "question": "Which topic should we cover next?",
        "options": options
    }
    
    poll_resp = requests.post(base_url, json={"query": add_poll_mutation, "variables": poll_vars}, headers=headers).json()
    
    if "errors" in poll_resp:
        return f"Discussion created at {discussion_url}, but Poll failed: {poll_resp['errors']}"
    
    return f"Success: {discussion_url}"

def clean_titles(titles):
    cleaned = []
    for t in titles:
        t = str(t).replace('“', '').replace('”', '').replace('—', '-').replace('"', "'")
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
    id_resp = requests.post("https://api.github.com/graphql", json={"query": query_ids, "variables": {"o": owner, "n": repo_name}}, headers={"Authorization": f"Bearer {token}"}).json()
    
    repo_id = id_resp['data']['repository']['id']
    cat_id = next(c['id'] for c in id_resp['data']['repository']['discussionCategories']['nodes'] if c['name'].lower() == 'polls')

    # Process V
    if v_rows:
        print("Processing Video Poll...")
        print(create_poll_flow(repo_id, cat_id, f"Video Poll: {os.path.basename(latest_file)}", clean_titles(v_rows[:8]), token))

    # Process S
    s_cleaned = clean_titles(s_rows)
    for i in range(0, len(s_cleaned), 8):
        chunk = s_cleaned[i:i+8]
        print(f"Processing Story Poll {(i//8)+1}...")
        print(create_poll_flow(repo_id, cat_id, f"Story Poll {(i//8)+1}: {os.path.basename(latest_file)}", chunk, token))

if __name__ == "__main__":
    create_poll()
