#!/usr/bin/env python3
import sys
import os
import subprocess
import json
import google.generativeai as genai
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

# --- 関数定義 ---

def get_issue_list(limit=30):
    """ghコマンドでIssueリストを取得する"""
    print("Fetching recent issues...", file=sys.stderr)
    try:
        cmd = ["gh", "issue", "list", "--limit", str(limit), "--json", "number,title,url"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        print("Error: Failed to fetch issue list.", file=sys.stderr)
        sys.exit(1)

def select_issue_interactively():
    """Issue一覧を表示してユーザーに選択させる"""
    issues = get_issue_list()

    if not issues:
        print("No open issues found.")
        sys.exit(0)

    print("\nSelect an issue to create a branch for:")
    print("-" * 60)

    # 見やすく整形して表示
    for i, issue in enumerate(issues):
        idx = i + 1
        print(f"[{idx}] #{issue['number']} {issue['title']}")

    print("-" * 60)
    print("[q] Quit")

    while True:
        try:
            choice = input("\nEnter number (or 'q' to quit): ").strip().lower()

            if choice in ['q', 'quit', 'exit']:
                print("Bye!")
                sys.exit(0)

            if not choice.isdigit():
                continue

            idx = int(choice)
            if 1 <= idx <= len(issues):
                return issues[idx - 1] # 選択されたIssueオブジェクトを返す
            else:
                print("Invalid number.")
        except KeyboardInterrupt:
            print("\nCanceled.")
            sys.exit(0)

def get_issue_detail(issue_number):
    """特定のIssue詳細を取得する"""
    print(f"Fetching Issue #{issue_number} info...")
    try:
        cmd = ["gh", "issue", "view", str(issue_number), "--json", "number,title,url"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error fetching issue: {e}", file=sys.stderr)
        sys.exit(1)

# --- メイン処理 ---

# 1. Issueの特定（引数 or 選択）
target_issue = None

if len(sys.argv) > 1:
    # 引数がある場合はそれをIDとして取得
    issue_number = sys.argv[1]
    target_issue = get_issue_detail(issue_number)
else:
    # 引数がない場合はリストから選択
    target_issue = select_issue_interactively()

# データ展開
issue_number = target_issue['number']
issue_title = target_issue['title']
issue_url = target_issue['url']

# 2. 情報表示
print("\n" + "="*40)
print(f"Issue: #{issue_number} {issue_title}")
print(f"URL  : {issue_url}")
print("="*40 + "\n")
print("Thinking of a branch name...", end="", flush=True)

# 3. Gemini生成
try:
    prompt_template = config['branch']['prompt']
    prompt = prompt_template.format(issue_number=issue_number, issue_title=issue_title)

    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    branch_name = response.text.strip()

    print(f"\r\033[KProposed Branch: \033[1;32m{branch_name}\033[0m")

except Exception as e:
    print(f"\nError calling Gemini API: {e}", file=sys.stderr)
    sys.exit(1)

# 4. 実行確認 (qで終了に対応)
try:
    print("\nPress [Enter] to create & checkout, or [q] to quit.")
    user_input = input("> ").strip().lower()

    if user_input in ['q', 'quit', 'exit']:
        print("Canceled.")
        sys.exit(0)

    print(f"Running: git checkout -b {branch_name}")
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    print("Done! 🚀")

except KeyboardInterrupt:
    print("\nCanceled.")
    sys.exit(0)
except subprocess.CalledProcessError:
    print("\nFailed to create branch.")
    sys.exit(1)