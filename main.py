import arxiv
from jinja2 import Template
import os
from datetime import datetime

# 1. 配置
SEARCH_QUERY = "cat:cs.AI"  # 例如：搜索人工智能类别
MAX_RESULTS = 5
OUTPUT_FILE = "index.html"

# 2. 抓取数据
def fetch_papers():
    client = arxiv.Client()
    search = arxiv.Search(
        query=SEARCH_QUERY,
        max_results=MAX_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate
    )
    results = list(client.results(search))
    
    papers = []
    for r in results:
        papers.append({
            "title": r.title,
            "authors": [a.name for a in r.authors],
            "summary": r.summary.replace('\n', ' '), # 简单清洗换行
            "url": r.entry_id,
            "published": r.published.strftime("%Y-%m-%d")
        })
    return papers

# 3. 生成 HTML
def generate_html(papers):
    # 简单的 HTML 模板字符串
    template_str = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>每日论文 {{ date }}</title>
        <style>
            body { font-family: sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
            .paper { border-bottom: 1px solid #eee; padding: 20px 0; }
            h2 { margin-top: 0; }
            .meta { color: #666; font-size: 0.9em; }
        </style>
    </head>
    <body>
        <h1>📅 Daily Papers: {{ date }}</h1>
        {% for paper in papers %}
        <div class="paper">
            <h2><a href="{{ paper.url }}">{{ paper.title }}</a></h2>
            <div class="meta">📅 {{ paper.published }} | 👥 {{ paper.authors|join(', ') }}</div>
            <p>{{ paper.summary }}</p>
        </div>
        {% endfor %}
    </body>
    </html>
    """
    template = Template(template_str)
    return template.render(date=datetime.now().strftime("%Y-%m-%d"), papers=papers)

# 4. 主函数
def main():
    print("开始抓取论文...")
    papers = fetch_papers()
    print(f"抓取到 {len(papers)} 篇论文。")
    
    html_content = generate_html(papers)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"成功生成 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
