import os
import glob
import pandas as pd
import requests
import json
import sys

def create_pollunit_poll(api_key, title, options):
    """
    Creates a PollUnit using the v1 API.
    """
    # Using the standard 'polls' endpoint for maximum stability
    url = "https://pollunit.com/api/v1/polls"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-App-Token": api_key
    }
    
    # PollUnit expects the configuration nested inside a 'poll' object
    payload = {
        "poll": {
            "title": title,
            "description": "Daily content selection for **Untold Minutes Tamil**. You can pick up to 3 topics!",
            "poll_type": "dot_voting",
            "multiple_votes_per_user": True,
            "max_votes_per_user": 3,
            "voting_type": "public",
            "options_attributes": [{"text": opt} for opt in options]
        }
    }
    
    try:
        resp = requests.post(url, json=payload, headers=headers)
        
        # If not successful, print the raw response to catch the error
        if resp.status_code not in [200, 201]:
            print(f"PollUnit Error {resp.status_code}: {resp.text}")
            return None, None
            
        data = resp.json()
        return data.get('url'), data.get('id')
    except Exception as e:
        print(f"Failed to communicate with PollUnit: {e}")
        return None, None

def post_to_github(repo_id, cat_id, title, poll_url, token):
    """
    Posts the Poll link back to your GitHub Discussion board.
    """
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
    variables = {
        "input": {
            "repositoryId": repo_id,
            "categoryId": cat_id,
            "title": title,
            "body": body
        }
    }
    
    try:
        resp = requests.post(url, json={"query": mutation, "variables": variables}, headers=headers).json()
        return resp.get('data', {}).get('createDiscussion', {}).get('discussion', {}).get('url')
    except Exception as e:
        print(f"GitHub Post Error: {e}")
        return None

def clean_titles(titles):
    """Trims titles and removes special characters that break JSON."""
    cleaned = []
    for t in titles:
        t = str(t).replace('"', "'").strip()
        if len(t) > 100: t = t[:97] + "..."
        cleaned.append(t)
    return cleaned

def main():
    # 1. Load Secrets & Environment
    token = os.getenv("GH_TOKEN")
    pu_token = os.getenv("POLLUNIT_TOKEN")
    owner = os.getenv("REPO_OWNER")
    repo_name = os.getenv("REPO_
