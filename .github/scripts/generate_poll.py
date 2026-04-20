import os
import glob
import pandas as pd
import requests
import json
import sys

def create_pollunit_poll(api_key, title, options):
    url = "https://pollunit.com/api/v1/polls"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-App-Token": api_key
    }
    payload = {
        "poll": {
            "title": title,
            "description": "Daily content selection for **Untold Minutes Tamil**. Pick up to 3 topics!",
            "poll_type": "dot_voting",
            "multiple_votes_per_user": True,
            "max_votes_per_user": 3,
            "voting_type": "public",
            "options_attributes": [{"text": opt} for opt in options]
        }
    }
    try:
        resp = requests.post(url, json=payload, headers=headers)
        if resp.status_code not in [200, 201]:
            print(f"PollUnit Error {resp.status_code}: {resp.text}")
            return None, None
        data = resp.json()
        return data.get('url'), data.get('id')
    except Exception as e:
        print(f"Failed to communicate with PollUnit: {e}")
        return None, None

def post_to_github(repo_id, cat_id, title, poll_url, token):
    url = "https://api.github.com/graphql"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = (
        f"### 🗳️ Multi-Select Poll: {title}\n\n"
        f"Help us decide the next stories for the channel! You can vote for multiple options.\n\n"
        f"👉 **[Click Here to Vote on PollUnit]({poll_url})**\n\n"
        f"--- \n"
        f"*This poll was automatically generated for Untold Minutes Tamil.*"
    )
    mutation = """
    mutation($input: CreateDiscussionInput!) {
      createDiscussion(input: $input) {
        discussion { url }
      }
    }
    """
    variables = {"input": {"repositoryId": repo_id, "categoryId": cat_id, "title": title, "body": body}}
    try:
        resp = requests.post(url, json={"query": mutation, "variables": variables}, headers=headers).json()
        return resp.get('data', {}).get('createDiscussion', {}).get('discussion', {}).get('url')
    except Exception as e:
        print(f"GitHub Post Error: {e}")
        return None

def clean_titles(titles):
    cleaned = []
    for t in titles:
        t = str(t).replace('"', "'").strip()
        if len(t) > 100: t = t[:97] + "..."
        cleaned.append(t)
    return cleaned

def main():
    token = os.getenv("GH_TOKEN")
    pu_token = os.getenv("POLLUNIT_TOKEN")
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_NAME")
    
    if not pu_token:
        print("Error: POLLUNIT_TOKEN is not set.")
        return

    path = "src/01_Planning/*.csv"
    files = glob.glob(path)
    if not files: return
    latest_file = max(files, key=os.path.getmtime)
    file_name = os.path.basename(latest_file)
    
    df = pd.read_csv(latest_file)
    df.columns = df.columns.str.strip().str.upper()
    v_rows = clean_titles(df[df['TYPE'].str.strip().str.upper() == 'V']['TITLE'].dropna().tolist())
    s_rows = clean_titles(df[df['TYPE'].str.strip().str.upper() == 'S']['TITLE'].dropna().tolist())

    query_ids = "query($o:String!,$n:String!){repository(owner:$o,name:$n){id discussionCategories(first:20){nodes{id name}}}}"
    try:
        id_resp = requests.post("https://api.github.com/graphql", 
                                json={"query": query_ids, "variables": {"o": owner, "n": repo_name}}, 
                                headers={"Authorization": f"Bearer {token}"}).json()
        repo_id = id_resp['data']['repository']['id']
        cat_id = next(c['id'] for c in id_resp['data']['repository']['discussionCategories']['nodes'] if c['name'].lower() == 'polls')
    except Exception as e:
        print(f"Failed to fetch GitHub IDs: {e}")
        return

    if v_rows:
        p_url, p_id = create_pollunit_poll(pu_token, f"Video Selection: {file_name}", v_rows[:10])
        if p_url: print(f"SUCCESS: Video Poll live at {post_to_github(repo_id, cat_id, f'Video Selection: {file_name}', p_url, token)}")

    for i in range(0, len(s_rows), 8):
        chunk = s_rows[i:i+8]
        p_num = (i // 8) + 1
        p_url, p_id = create_pollunit_poll(pu_token, f"Story Selection {p_num}: {file_name}", chunk)
        if p_url: print(f"SUCCESS: Story Poll {p_num} live at {post_to_github(repo_id, cat_id, f'Story Selection {p_num}', p_url, token)}")

if __name__ == "__main__":
    main()
