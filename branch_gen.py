#!/usr/bin/env python3
import sys
import os
import subprocess
import json
import google.generativeai as genai
import questionary  # 追加
from questionary import Choice

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
        # 見やすさのために少し多めに取得
        cmd = ["gh", "issue", "list", "--limit", str(limit), "--json", "number,title,url"]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(result.stdout)
    except subprocess.CalledProcessError:
        print("Error: Failed to fetch issue list.", file=sys.stderr)
        sys.exit(1)

def select_issue_interactively():
    """questionaryを使ってカーソル選択させる"""
    issues = get_issue_list()

    if not issues:
        print("No open issues found.")
        sys.exit(0)

    # 選択肢の作成
    choices = []
    for issue in issues:
        # 表示名: "#88 Issueタイトル"
        display_text = f"#{issue['number']} {issue['title']}"
        # value: Issueオブジェクトそのもの
        choices.append(Choice(title=display_text, value=issue))

    # キャンセル用オプションを追加
    choices.append(Choice(title="Cancel (Exit)", value="CANCEL"))

    # 選択メニューを表示
    try:
        selection = questionary.select(
            "Select an issue to create a branch for:",
            choices=choices,
            qmark="?",
            pointer="❯",
            use_indicator=True,
            style=questionary.Style([
                ('qmark', 'fg:#FF9D00 bold'),       # 疑問符の色
                ('question', 'bold'),               # 質問文のスタイル
                ('pointer', 'fg:#FF9D00 bold'),     # カーソルの色
                ('highlighted', 'fg:#FF9D00 bold'), # 選択中の項目の色
                ('selected', 'fg:#cc5454'),         # 決定後の色
            ])
        ).ask() # ask()で実行

        # キャンセルまたはCtrl+Cの場合
        if selection == "CANCEL" or selection is None:
            print("Canceled.")
            sys.exit(0)

        return selection

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

# 4. 実行確認 (y/n選択もquestionary化)
try:
    # 単純な yes/no は confirm が便利
    confirmed = questionary.confirm(
        f"Create & checkout '{branch_name}'?",
        default=True
    ).ask()

    if not confirmed:
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