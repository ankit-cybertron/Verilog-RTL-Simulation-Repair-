import os
from huggingface_hub import HfApi

def deploy():
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN missing")
        return
    api = HfApi(token=token)
    
    # Try to get the user's username
    username = api.whoami()["name"]
    print(f"Logged in as: {username}")
    
    repo_id = f"{username}/rtlrepair-env"
    
    # Create repo
    print(f"Creating Space: {repo_id}")
    try:
        api.create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=False,
            exist_ok=True
        )
        print("Space created or already exists!")
    except Exception as e:
        print(f"Error creating repo: {e}")
        
if __name__ == "__main__":
    deploy()
