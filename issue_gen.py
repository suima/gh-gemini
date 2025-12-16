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

# --- 入力処理 ---

def get_input_content():
    """引数に応じてパイプまたはクリップボードから入力を取得"""
    content = ""

    # オプション判定
    use_clipboard = ("--clipboard" in sys.argv or "-c" in sys.argv)

    if use_clipboard:
        try:
            import pyperclip
            content = pyperclip.paste()
            print("📋 Reading from clipboard...")
        except ImportError:
            print("Error: 'pyperclip' is not installed. Run `pip install pyperclip`.", file=sys.stderr)
            sys.exit(1)
    else:
        # 標準入力（パイプ）のチェック
        if not sys.stdin.isatty():
            # パイプからデータが来ている場合
            content = sys.stdin.read()
        else:
            # パイプもクリップボード指定もない場合
            print("Error: No input provided.")
            print("Usage:")
            print("  cat info.txt | gh gemini issue      (Pipe)")
            print("  gh gemini issue -c                  (Clipboard)")
            sys.exit(1)

    if not content.strip():
        print("Error: Input is empty.", file=sys.stderr)
        sys.exit(1)

    return content.strip()

# --- メイン処理 ---

input_text = get_input_content()

print(f"Analyzing input ({len(input_text)} chars) and generating issue...", end="", flush=True)

try:
    # プロンプト作成
    prompt_template = config['issue']['prompt']
    prompt = prompt_template.format(input_text=input_text)

    # Gemini呼び出し
    model = genai.GenerativeModel(MODEL_NAME)
    # JSONモードを強制するために response_mime_type を指定できるモデルならしたいが、
    # 汎用性を高めるためプロンプト指示 + パース処理で対応
    response = model.generate_content(prompt)
    generated_text = response.text.strip()

    # Markdownのコードブロック ```json ... ``` を除去してパース
    json_match = re.search(r'\{.*\}', generated_text, re.DOTALL)
    if json_match:
        json_str = json_match.group(0)
    else:
        json_str = generated_text

    issue_data = json.loads(json_str)

    title = issue_data.get("title", "No Title")
    body = issue_data.get("body", "")

    print(f"\r\033[K\033[1;36mProposed Issue:\033[0m")
    print("-" * 60)
    print(f"\033[1mTitle:\033[0m {title}")
    print("-" * 60)
    print(body)
    print("-" * 60)

except json.JSONDecodeError:
    print("\nError: Failed to parse JSON from Gemini response.", file=sys.stderr)
    print(f"Raw output:\n{generated_text}", file=sys.stderr)
    sys.exit(1)
except Exception as e:
    print(f"\nError calling Gemini API: {e}", file=sys.stderr)
    sys.exit(1)

# --- ユーザー確認と実行 ---
try:
    confirmed = questionary.confirm(
        "Create this Issue?",
        default=True
    ).ask()

    if not confirmed:
        print("Canceled.")
        sys.exit(0)

    print("Creating Issue...")

    # gh issue create コマンドを実行
    cmd = ["gh", "issue", "create", "--title", title, "--body", body]

    # ブラウザで開くかどうかのオプションなどはお好みで追加可能
    # cmd.append("--web")

    subprocess.run(cmd, check=True)
    print("Done! 🚀")

except KeyboardInterrupt:
    print("\nCanceled.")
    sys.exit(0)
except subprocess.CalledProcessError:
    print("\nFailed to create issue.")
    sys.exit(1)