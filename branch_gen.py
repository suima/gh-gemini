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

# --- 処理開始 ---

if len(sys.argv) < 2:
    print("Usage: gh gemini branch <issue-number>", file=sys.stderr)
    sys.exit(1)

issue_number = sys.argv[1]

print(f"Fetching Issue #{issue_number} info...")
try:
    cmd = ["gh", "issue", "view", issue_number, "--json", "title,url"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    issue_data = json.loads(result.stdout)
    issue_title = issue_data['title']
    issue_url = issue_data['url']
except Exception as e:
    print(f"Error fetching issue: {e}", file=sys.stderr)
    sys.exit(1)

print("\n" + "="*40)
print(f"Issue: #{issue_number} {issue_title}")
print(f"URL  : {issue_url}")
print("="*40 + "\n")
print("Thinking of a branch name...", end="", flush=True)

# プロンプトの構築（YAMLの文字列に埋め込み）
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

# ユーザー確認と実行
try:
    user_input = input("\nPress [Enter] to create & checkout, or [Ctrl+C] to cancel.")
    print(f"Running: git checkout -b {branch_name}")
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    print("Done! 🚀")
except KeyboardInterrupt:
    print("\nCanceled.")
    sys.exit(0)
except subprocess.CalledProcessError:
    print("\nFailed to create branch.")
    sys.exit(1)