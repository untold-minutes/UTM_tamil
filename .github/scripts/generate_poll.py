import os
import glob
import pandas as pd
import requests
import json
import sys

def create_reaction_poll(repo_id, cat_id, title, options, token):
    base_url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Create the Body text with numbered options
    body_text = "### 🗳️ Vote for the next topic!\n\n"
    for i, opt in enumerate(options, 1):
        body_text += f"{i}. {opt}\n"
    body_text += "\n**How to vote:** React to this discussion or reply with the number of your choice!"

    mutation = """
    mutation($input: CreateDiscussionInput!) {
      createDiscussion(input: $input) {
        discussion { url }
      }
    }
    """
    
    variables = {
        "input": {
            "repositoryId": repo_id,
            "categoryId": cat_id,
            "title": title,
            "body": body_text
        }
    }
    
    resp = requests.post(base_url, json={"query": mutation, "variables": variables}, headers=headers).json()
    
    if "errors" in resp:
        return f"Failed: {resp['errors']}"
    
    return f"Success! Topic list live at: {resp['data']['createDiscussion']['discussion']['url']}"

def clean_titles(titles):
    cleaned = []
    for t in titles:
        t = str(t).replace('"', "'").strip()
        cleaned.append(t)
    return cleaned

def create_poll():
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files: sys.exit(0)
    
    latest_file = max(files, key=os.path.getmtime)
    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()
    
    v_rows = df[df['TYPE'].str.strip().str.upper() == 'V']['TITLE'].dropna().tolist()
    s_rows = df[df['TYPE'].str.strip().str.upper() == 'S']['TITLE'].dropna().tolist()

    token = os.getenv("GH_TOKEN")
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")
    
    query_ids = "query($o:String!,$n:String!){repository(owner:$o,name:$n){id discussionCategories(first:20){nodes{id name}}}}"
    id_resp = requests.post("https://api.github.com/graphql", json={"query": query_ids, "variables": {"o": owner, "n": repo_name}}, headers={"Authorization": f"Bearer {token}"}).json()
    
    repo_id = id_resp['data']['repository']['id']
    cat_id = next(c['id'] for c in id_resp['data']['repository']['discussionCategories']['nodes'] if c['name'].lower() == 'polls')

    if v_rows:
        print(create_reaction_poll(repo_id, cat_id, f"Video Selection: {os.path.basename(latest_file)}", clean_titles(v_rows[:8]), token))

    s_cleaned = clean_titles(s_rows)
    for i in range(0, len(s_cleaned), 8):
        print(create_reaction_poll(repo_id, cat_id, f"Story Selection Part {(i//8)+1}", s_cleaned[i:i+8], token))

if __name__ == "__main__":
    create_poll()
