import os
import glob
import pandas as pd
import requests
import json
import sys

def create_pollunit_poll(api_key, title, options):
    """
    Creates a PollUnit with Multiple Choice/Dot Voting enabled.
    """
    url = "https://pollunit.com/api/v1/poll_units"
    headers = {
        "Content-Type": "application/json",
        "X-App-Token": api_key
    }
    
    payload = {
        "title": title,
        "poll_type": "dot_voting",  # Allows users to show preference strength
        "description": "Daily content selection for **Untold Minutes Tamil**. You can vote for multiple topics!",
        "options_attributes": [{"text": opt} for opt in options],
        "multiple_votes_per_user": True,
        "max_votes_per_user": 3,     # Users can pick their top 3
        "voting_type": "public"      # No login required for viewers
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        return data.get('url'), data.get('id')
    except Exception as e:
        print(f"PollUnit Error: {e}")
        return None, None

def post_to_github(repo_id, cat_id, title, poll_url, token):
    """
    Posts the PollUnit link to GitHub Discussions.
    """
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    body = f"### 🗳️ Multi-Select Poll is Live!\n\nPlease click the link below to vote for our next stories. You can choose up to 3 topics!\n\n**Vote Here:** {poll_url}\n\n*Results will be announced automatically once the poll closes.*"

    mutation = """
    mutation($input: CreateDiscussionInput!) {
      createDiscussion(input: $input) {
        discussion { url }
      }
    }
    """
    vars = {
        "input": {
            "repositoryId": repo_id,
            "categoryId": cat_id,
            "title": title,
            "body": body
        }
    }
    
    resp = requests.post(url, json={"query": mutation, "variables": vars}, headers=headers).json()
    return resp.get('data', {}).get('createDiscussion', {}).get('discussion', {}).get('url')

def clean_titles(titles):
    return [str(t).strip()[:100] for t in titles]

def main():
    # 1. Environment & Files
    token = os.getenv("GH_TOKEN")
    pu_token = os.getenv("POLLUNIT_TOKEN")
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")
    
    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files: return
    latest_file = max(files, key=os.path.getmtime)
    
    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()
    v_rows = clean_titles(df[df['TYPE'] == 'V']['TITLE'].dropna().tolist())
    s_rows = clean_titles(df[df['TYPE'] == 'S']['TITLE'].dropna().tolist())

    # 2. Get GitHub IDs
    query = "query($o:String!,$n:String!){repository(owner:$o,name:$n){id discussionCategories(first:20){nodes{id name}}}}"
    id_resp = requests.post("https://api.github.com/graphql", json={"query": query, "variables": {"o": owner, "n": repo_name}}, headers={"Authorization": f"Bearer {token}"}).json()
    repo_id = id_resp['data']['repository']['id']
    cat_id = next(c['id'] for c in id_resp['data']['repository']['discussionCategories']['nodes'] if c['name'].lower() == 'polls')

    # 3. Create Video Poll
    if v_rows:
        p_url, p_id = create_pollunit_poll(pu_token, f"Video Selection: {os.path.basename(latest_file)}", v_rows[:8])
        if p_url:
            disc_url = post_to_github(repo_id, cat_id, f"Video Poll: {os.path.basename(latest_file)}", p_url, token)
            print(f"Video Poll Live: {disc_url}")

    # 4. Create Story Polls
    for i in range(0, len(s_rows), 8):
        chunk = s_rows[i:i+8]
        p_num = (i // 8) + 1
        p_url, p_id = create_pollunit_poll(pu_token, f"Story Selection Part {p_num}", chunk)
        if p_url:
            disc_url = post_to_github(repo_id, cat_id, f"Story Poll {p_num}: {os.path.basename(latest_file)}", p_url, token)
            print(f"Story Poll {p_num} Live: {disc_url}")

if __name__ == "__main__":
    main()
