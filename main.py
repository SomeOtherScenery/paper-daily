import hashlib
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path

import arxiv
import requests
from jinja2 import Environment, FileSystemLoader, select_autoescape


KEYWORDS = "robot"
ARXIV_SEARCH_QUERY = "cat:cs.AI OR cat:cs.RO"
MAX_RESULTS = 10
OUTPUT_FILE = "result/index.html"
TRANSLATION_CACHE_FILE = "result/translation_cache.json"
MAX_FETCH_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 5
TRANSLATION_REQUEST_TIMEOUT = 30
TRANSLATION_MAX_RETRIES = 3
PROJECT_ROOT = Path(__file__).resolve().parent
ENV_FILE = PROJECT_ROOT / ".env"


def load_project_env(env_path):
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]

        # Respect CI-provided environment variables instead of overwriting them.
        os.environ.setdefault(key, value)


load_project_env(ENV_FILE)


def env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def normalize_summary(text):
    if not text:
        return "No abstract available."
    return " ".join(text.split())


def get_hot_papers(keywords, years=2):
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    start_year = max(datetime.now().year - max(years, 1) + 1, 2000)
    params = {
        "query": keywords,
        "year": f"{start_year}-{datetime.now().year}",
        "fields": "title,authors,abstract,citationCount,url,externalIds,year",
        "limit": MAX_RESULTS,
        "sort": "citationCount:desc",
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        print(f"[ERROR] Semantic Scholar API request failed: {exc}")
        return []

    hot_papers = []
    for item in data.get("data", []):
        github_link = None
        external_ids = item.get("externalIds") or {}
        if external_ids.get("Github"):
            github_link = f"https://github.com/{external_ids['Github']}"

        hot_papers.append(
            {
                "title": item.get("title", "N/A"),
                "authors": [author.get("name", "Unknown") for author in item.get("authors", [])],
                "summary": normalize_summary(item.get("abstract")),
                "url": item.get("url", "N/A"),
                "published": str(item.get("year", "Unknown")),
                "citations": item.get("citationCount", 0),
                "code_url": github_link,
            }
        )

    return hot_papers


def get_code_url(arxiv_result):
    search_text = arxiv_result.comment or arxiv_result.summary or ""
    match = re.search(r"github\.com/([\w\-\.]+/[\w\-\.]+)", search_text)
    if match:
        return f"https://{match.group(0)}"
    return None


def fetch_papers():
    client = arxiv.Client(
        page_size=min(MAX_RESULTS, 50),
        delay_seconds=5,
        num_retries=5,
    )
    search = arxiv.Search(
        query=ARXIV_SEARCH_QUERY,
        max_results=MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
    )

    backoff_seconds = INITIAL_BACKOFF_SECONDS
    results = []
    for attempt in range(1, MAX_FETCH_RETRIES + 1):
        try:
            results = list(client.results(search))
            break
        except arxiv.HTTPError as exc:
            is_rate_limited = "HTTP 429" in str(exc)
            if (not is_rate_limited) or attempt == MAX_FETCH_RETRIES:
                raise
            print(
                f"arXiv API rate limit reached (attempt {attempt}/{MAX_FETCH_RETRIES}). "
                f"Retrying in {backoff_seconds}s..."
            )
            time.sleep(backoff_seconds)
            backoff_seconds *= 2

    papers = []
    for result in results:
        papers.append(
            {
                "title": result.title,
                "authors": [author.name for author in result.authors],
                "summary": normalize_summary(result.summary),
                "url": result.entry_id,
                "published": result.published.strftime("%Y-%m-%d"),
                "categories": result.categories,
                "id": result.get_short_id(),
                "code_url": get_code_url(result),
            }
        )
    return papers


def load_translation_cache(cache_path):
    if not cache_path.exists():
        return {}

    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        print(f"[WARN] Translation cache is broken: {cache_path}. Rebuilding it.")
        return {}


def save_translation_cache(cache_path, cache):
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def build_summary_cache_key(title, summary):
    return hashlib.sha256(f"{title}\n{summary}".encode("utf-8")).hexdigest()


class DeepSeekTranslator:
    def __init__(self):
        self.enabled = env_flag("ENABLE_ABSTRACT_TRANSLATION", False)
        self.api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
        self.model = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip()
        self.api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com").rstrip("/")
        self.target_language = os.getenv("TRANSLATION_TARGET_LANGUAGE", "Simplified Chinese").strip()
        self.session = requests.Session()

    def is_ready(self):
        return self.enabled and bool(self.api_key and self.model)

    def translate(self, text):
        if not self.is_ready() or not text or text == "No abstract available.":
            return None

        payload = {
            "model": self.model,
            "temperature": 0.2,
            "thinking": {"type": "disabled"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You translate scientific paper abstracts accurately. "
                        "Keep technical terms precise and do not add commentary."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Translate the following abstract into {self.target_language}. "
                        "Return translation only.\n\n"
                        f"{text}"
                    ),
                },
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        delay_seconds = 2
        last_error = None
        for attempt in range(1, TRANSLATION_MAX_RETRIES + 1):
            try:
                response = self.session.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=TRANSLATION_REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except Exception as exc:
                last_error = exc
                if attempt == TRANSLATION_MAX_RETRIES:
                    break
                print(
                    f"[WARN] Translation request failed (attempt {attempt}/{TRANSLATION_MAX_RETRIES}). "
                    f"Retrying in {delay_seconds}s..."
                )
                time.sleep(delay_seconds)
                delay_seconds *= 2

        print(f"[WARN] Translation skipped after repeated failures: {last_error}")
        return None


def translate_papers(papers):
    translator = DeepSeekTranslator()
    if not translator.enabled:
        return papers

    if not translator.is_ready():
        print(
            "[WARN] Abstract translation is enabled, but DEEPSEEK_API_KEY is missing. "
            "Rendering original abstracts only."
        )
        return papers

    cache_path = Path(TRANSLATION_CACHE_FILE)
    cache = load_translation_cache(cache_path)
    cache_changed = False

    for paper in papers:
        cache_key = build_summary_cache_key(paper["title"], paper["summary"])
        translated = cache.get(cache_key)
        if translated is None:
            translated = translator.translate(paper["summary"])
            if translated:
                cache[cache_key] = translated
                cache_changed = True

        if translated:
            paper["summary_zh"] = translated

    if cache_changed:
        save_translation_cache(cache_path, cache)

    return papers


def generate_html(papers):
    env = Environment(
        loader=FileSystemLoader("./templates"),
        autoescape=select_autoescape(),
    )
    template = env.get_template("main_page.html")
    return template.render(date=datetime.now().strftime("%Y-%m-%d"), papers=papers)


def main():
    print("Start fetching papers...")
    try:
        # papers = get_hot_papers(KEYWORDS)
        papers = fetch_papers()
    except arxiv.HTTPError as exc:
        print(f"Fetch failed: {exc}")
        print("Hint: this may be an arXiv 429 rate-limit error. Please retry later.")
        return

    print(f"Fetched {len(papers)} papers.")
    papers = translate_papers(papers)
    html_content = generate_html(papers)

    output_path = Path(OUTPUT_FILE)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html_content, encoding="utf-8")
    print(f"Generated {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
