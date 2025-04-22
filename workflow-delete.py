import requests, os

# === CONFIG ===
GITHUB_TOKEN = os.getenv("GIT_API_TOKEN")
REPO = "LeftandRights/sshx"  # format: user/repo
HEADERS = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}

# === GET ALL WORKFLOW RUNS ===
runs_url = f"https://api.github.com/repos/{REPO}/actions/runs"
response = requests.get(runs_url, headers=HEADERS)
runs = response.json().get("workflow_runs", [])

# === DELETE FAILED RUNS ===
for run in runs:
    run_id = run["id"]
    status = run["status"]
    conclusion = run["conclusion"]

    if status == "in_progress":
        continue

    del_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}"
    del_resp = requests.delete(del_url, headers=HEADERS)

    if del_resp.status_code == 204:
        print(f"✅ Deleted run {run_id}")
    else:
        print(f"❌ Failed to delete run {run_id} — {del_resp.status_code}")
