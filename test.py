
from jinja2 import Environment, FileSystemLoader, select_autoescape


OUTPUT_FILE="result/test.html"

env = Environment(
    loader=FileSystemLoader("./templates"),
    autoescape=select_autoescape()
)

template = env.get_template("test.html")
temp_str = template.render(
    user='wcf'
)

with open(OUTPUT_FILE,'w', encoding='utf8') as f:
    f.write(temp_str)
