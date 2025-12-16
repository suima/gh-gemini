#!/usr/bin/env python3
import sys
import os
import subprocess
import google.generativeai as genai

# --- 設定 ---
# APIキー取得
api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("Error: GEMINI_API_KEY environment variable is not set.", file=sys.stderr)
    sys.exit(1)

genai.configure(api_key=api_key)

# モデル (無料枠対応の最新Flashモデル)
MODEL_NAME = 'gemini-flash-latest'

# --- メイン処理 ---

# 1. ステージングされた差分を取得
try:
    # git diff --cached の出力を取得
    diff_process = subprocess.run(
        ["git", "diff", "--cached"],
        capture_output=True,
        text=True,
        check=True
    )
    diff_content = diff_process.stdout.strip()

    if not diff_content:
        print("Error: No staged changes found. Please run 'git add' first.", file=sys.stderr)
        sys.exit(1)

except subprocess.CalledProcessError:
    print("Error: Not a git repository or git command failed.", file=sys.stderr)
    sys.exit(1)

# 2. Geminiにコミットメッセージを生成させる
print("Analyzing changes and generating commit message...", end="", flush=True)

prompt = f"""
あなたは熟練したエンジニアです。以下の `git diff` の内容に基づいて、適切なgit commit messageを作成してください。

【制約】
- フォーマットは "Conventional Commits" に従うこと (例: feat: ..., fix: ..., refactor: ...)。
- 1行目は「タイプ: 概要」の形式で書くこと。
- 3行目以降に、箇条書きで詳細な変更点を記載すること。
- 言語は「日本語」で出力すること。
- 出力にはMarkdownのコードブロック(```)を含めず、メッセージのテキストのみを返すこと。

【変更内容】
{diff_content}
"""

try:
    model = genai.GenerativeModel(MODEL_NAME)
    response = model.generate_content(prompt)
    commit_message = response.text.strip()

    # 余計なバッククォートがあれば除去
    commit_message = commit_message.replace("```", "").strip()

    print(f"\r\033[K\033[1;36mProposed Commit Message:\033[0m") # シアン色で見出し
    print("-" * 40)
    print(commit_message)
    print("-" * 40)

except Exception as e:
    print(f"\nError calling Gemini API: {e}", file=sys.stderr)
    sys.exit(1)

# 3. ユーザー確認と実行
try:
    print("\nPress [Enter] to commit, [e] to edit manually, or [Ctrl+C] to cancel.")
    user_input = input("> ").strip().lower()

    if user_input == 'e':
        # 手動編集モード（一時ファイルを使ってエディタを開くなどは複雑になるため、コマンドを表示して終了）
        print("\nCopy the message above and run git commit manually.")
        sys.exit(0)

    # Enter (空文字) の場合のみ実行
    if user_input == "":
        print("Committing...")
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        print("Done! 🚀")
    else:
        print("Canceled.")

except KeyboardInterrupt:
    print("\nCanceled.")
    sys.exit(0)
except subprocess.CalledProcessError:
    print("\nFailed to commit.")
    sys.exit(1)