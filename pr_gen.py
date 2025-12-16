#!/usr/bin/env python3
import sys
import os
import subprocess
import json
import re
import google.generativeai as genai
import questionary
# common.py をインポートするためのパス設定
sys.path.append(os.path.dirname(os.path.realpath(__file__)))
import common

# --- 設定読み込み ---
config = common.load_config()
api_key = os.environ.get(config['global']['api_env_var'])
MODEL_NAME = config['global']['model']

if not api_key:
    print(f"Error: {config['global']['api_env_var']} environment variable is not set.", file=sys.stderr)
    sys.exit(1)

genai.configure(api_key=api_key)

# --- Git情報の取得と操作 ---

def get_current_branch():
    try:
        res = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except subprocess.CalledProcessError:
        print("Error: Not a git repository.", file=sys.stderr)
        sys.exit(1)

def check_and_push_branch(branch_name):
    """リモートにブランチがあるか確認し、なければプッシュを促す"""
    print(f"Checking remote branch for '{branch_name}'...", end="", flush=True)

    # git ls-remote でリモートブランチの存在確認
    # 戻り値が0なら存在する、それ以外なら存在しない（または通信エラー）
    cmd = ["git", "ls-remote", "--exit-code", "--heads", "origin", branch_name]
    result = subprocess.run(cmd, capture_output=True)

    if result.returncode == 0:
        print(" OK (Exists).")
        return True # 存在する

    print(" Not found.")

    # 存在しない場合、プッシュするか聞く
    should_push = questionary.confirm(
        f"Branch '{branch_name}' does not exist on remote. Push now?",
        default=True
    ).ask()

    if should_push:
        print(f"Running: git push -u origin {branch_name}")
        try:
            subprocess.run(["git", "push", "-u", "origin", branch_name], check=True)
            print("Push successful! 🚀")
            return True
        except subprocess.CalledProcessError:
            print("Error: Failed to push branch.", file=sys.stderr)
            sys.exit(1)
    else:
        print("Cannot create PR without remote branch. Exiting.")
        sys.exit(0)

def get_commit_logs(base_branch="main"):
    """base_branchとの差分コミットログを取得"""
    try:
        # mainが存在しない場合などを考慮して簡易的に取得
        cmd = ["git", "log", f"{base_branch}..HEAD", "--pretty=format:- %s"]
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode != 0 or not res.stdout.strip():
            # 差分が取れない場合は直近5件
            cmd = ["git", "log", "-n", "5", "--pretty=format:- %s"]
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return res.stdout.strip()
    except Exception:
        return "No commit logs found."

def get_linked_issue_info(branch_name):
    """ブランチ名 (88-fix-...) からIssue情報を取得"""
    match = re.match(r'^(\d+)-', branch_name)
    if not match:
        return "None", "None"

    issue_number = match.group(1)
    try:
        cmd = ["gh", "issue", "view", issue_number, "--json", "title"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        return issue_number, data.get('title', '')
    except:
        return issue_number, "Unknown Title"

# --- メイン処理 ---

branch_name = get_current_branch()

# リモートブランチの確認とプッシュ
check_and_push_branch(branch_name)

commit_logs = get_commit_logs()
issue_number, issue_title = get_linked_issue_info(branch_name)

print(f"\nCollecting context for branch '{branch_name}'...")
if issue_number != "None":
    print(f"Found related issue: #{issue_number} {issue_title}")

print("Generating PR description...", end="", flush=True)

try:
    # プロンプト作成
    prompt_template = config['pr']['prompt']
    prompt = prompt_template.format(
        branch_name=branch_name,
        issue_number=issue_number,
        issue_title=issue_title,
        commit_logs=commit_logs
    )

    # Gemini呼び出し
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    generated_text = response.text.strip()

    # JSONパース
    json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
    json_str = json_match.group(0) if json_match else generated_text
    pr_data = json.loads(json_str)

    title = pr_data.get("title", f"Change {branch_name}")
    body = pr_data.get("body", "")

    print(f"\r\033[K\033[1;36mProposed Pull Request:\033[0m")
    print("-" * 60)
    print(f"\033[1mTitle:\033[0m {title}")
    print("-" * 60)
    print(body)
    print("-" * 60)

except Exception as e:
    print(f"\nError calling Gemini API: {e}", file=sys.stderr)
    sys.exit(1)

# --- ユーザー確認と実行 ---
try:
    confirmed = questionary.confirm(
        "Create this Pull Request?",
        default=True
    ).ask()

    if not confirmed:
        print("Canceled.")
        sys.exit(0)

    print("Creating PR...")

    # gh pr create 実行
    cmd = ["gh", "pr", "create", "--title", title, "--body", body]

    # 必要ならWebで開くオプションを追加
    # cmd.append("--web")

    subprocess.run(cmd, check=True)
    print("Done! 🚀")

except KeyboardInterrupt:
    print("\nCanceled.")
    sys.exit(0)
except subprocess.CalledProcessError as e:
    print("\nFailed to create PR.")
    sys.exit(1)