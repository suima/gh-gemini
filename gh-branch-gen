#!/usr/bin/env python3
import sys
import os
import subprocess
import json
import google.generativeai as genai

# --- 設定 ---
# APIキーの取得
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
    sys.exit(1)

genai.configure(api_key=api_key)

# モデル設定 (無料枠で安定して使えるモデル)
MODEL_NAME = 'gemini-flash-latest'

# --- 処理開始 ---

# 1. 引数チェック
if len(sys.argv) < 2:
    print("Usage: gh branch-gen <issue-number>", file=sys.stderr)
    sys.exit(1)

issue_number = sys.argv[1]

# 2. Issue情報の取得 (ghコマンド)
print(f"Fetching Issue #{issue_number} info...")
try:
    # タイトルとURLをJSON形式で取得
    cmd = ["gh", "issue", "view", issue_number, "--json", "title,url"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    issue_data = json.loads(result.stdout)

    issue_title = issue_data['title']
    issue_url = issue_data['url']

except subprocess.CalledProcessError:
    print(f"Error: Could not fetch issue #{issue_number}. Check if issue exists.", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError:
    print("Error: Failed to parse GitHub CLI output.", file=sys.stderr)
    sys.exit(1)

# 3. 取得した内容を表示
print("\n" + "="*40)
print(f"Issue: #{issue_number} {issue_title}")
print(f"URL  : {issue_url}")
print("="*40 + "\n")
print("Thinking of a branch name...", end="", flush=True)

# 4. Geminiでブランチ名を生成
prompt = f"""
以下のGitHub IssueのIDとタイトルから、適切なgit branch名を1つだけ提案してください。

【ルール】
- フォーマット: {issue_number}-<kebab-case-description>
- 英語で簡潔に表現すること。
- 余計な説明や装飾は一切不要。ブランチ名の文字列のみを返すこと。

【Issue情報】
ID: {issue_number}
Title: {issue_title}
"""

try:
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    branch_name = response.text.strip()

    # 思考中メッセージを上書きするように改行
    print(f"\r\033[KProposed Branch: \033[1;32m{branch_name}\033[0m") # 緑色で表示

except Exception as e:
    print(f"\nError calling Gemini API: {e}", file=sys.stderr)
    sys.exit(1)

# 5. ユーザー確認と実行
try:
    user_input = input("\nPress [Enter] to create & checkout, or [Ctrl+C] to cancel.")

    # Enterが押されたら実行
    print(f"Running: git checkout -b {branch_name}")
    subprocess.run(["git", "checkout", "-b", branch_name], check=True)
    print("Done! 🚀")

except KeyboardInterrupt:
    print("\nCanceled.")
    sys.exit(0)
except subprocess.CalledProcessError:
    # gitコマンドが失敗した場合（同名ブランチがあるなど）
    print("\nFailed to create branch.")
    sys.exit(1)