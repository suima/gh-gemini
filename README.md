# gh-branch-gen
GitHub Issue の内容を元に、Google Gemini AI が適切なブランチ名を自動提案・作成する GitHub CLI 拡張機能

## 依存ライブラリのインストール
`pip install google-generativeai`

## 拡張機能として登録
`gh extension install .`

## APIキーの設定
`export GEMINI_API_KEY="ここに取得したAPIキー"`

# 使い方
`gh branch-gen <ISSUE_NUMBER>`

# 設定
デフォルトでは gemini-flash-latest を使用。
モデルを変更したい場合は、スクリプト内の以下の変数を編集。

``` python
# gh-branch-gen
MODEL_NAME = 'gemini-flash-latest'
```

# トラブルシューティング

- `404 models/... is not found` エラーが出る：`google-generativeai` ライブラリが古い可能性がある。以下でアップデートする。 `pip install --upgrade google-generativeai`
- `Quota exceeded エラーが出る`：指定しているモデルが無料枠に対応していない、または割り当て上限に達している。`gemini-flash-latest` を使用する。