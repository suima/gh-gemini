import os
import sys
import yaml

def load_config():
    """config.yamlを読み込んで辞書として返す"""
    # このスクリプトのあるディレクトリを取得
    base_dir = os.path.dirname(os.path.realpath(__file__))
    config_path = os.path.join(base_dir, "config.yaml")

    if not os.path.exists(config_path):
        print(f"Error: Config file not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"Error parsing config.yaml: {e}", file=sys.stderr)
        sys.exit(1)