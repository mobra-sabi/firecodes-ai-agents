import json, yaml
from pathlib import Path
from playwright.sync_api import sync_playwright

def load_yaml(path: str):
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Missing {path}")
    return yaml.safe_load(p.read_text(encoding="utf-8"))

def main():
    settings = load_yaml("config/settings.yaml")
    policies = load_yaml("config/policies.yaml")
    print("settings keys:", list(settings.keys()))
    print("policies keys:", list(policies.keys()))
    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()
        page.goto("https://example.com", timeout=30000)
        print("playwright title:", page.title())
        browser.close()

if __name__ == "__main__":
    main()
