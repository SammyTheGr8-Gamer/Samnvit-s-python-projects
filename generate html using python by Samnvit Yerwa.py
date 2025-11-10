import os
import argparse
from datetime import datetime
import webbrowser
import textwrap

DEFAULT_CSS = """
body {
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial;
    margin: 32px;
    background: #f7f8fb;
    color: #222;
}
.container {
    max-width: 900px;
    margin: auto;
    background: #fff;
    padding: 24px;
    border-radius: 10px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.06);
}
h1 { color: #0a66c2; margin-top: 0; }
.footer { font-size: 0.9em; color: #666; margin-top: 18px; }
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
{css}
</style>
</head>
<body>
  <div class="container">
    <h1>{heading}</h1>
    {body}
    <div class="footer">
      Generated: {date} • File: {filename}
    </div>
  </div>
</body>
</html>
"""

def sanitize_filename(name: str) -> str:
    name = name.strip()
    if not name:
        name = "index.html"
    if not name.lower().endswith(".html"):
        name += ".html"
    return name

def paragraphs_from_text(text: str) -> str:
    # Convert double-newlines into paragraph tags, keep single newlines as line-breaks
    parts = [p.strip() for p in text.strip().split("\n\n") if p.strip()]
    html_parts = []
    for p in parts:
        p = p.replace("\n", "<br/>")
        html_parts.append(f"<p>{p}</p>")
    return "\n    ".join(html_parts)

def build_html(filename: str, title: str, heading: str, body_text: str, css: str) -> str:
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    body_html = paragraphs_from_text(body_text or "")
    return HTML_TEMPLATE.format(title=title or "Untitled",
                                heading=heading or title or "Hello",
                                body=body_html,
                                css=css or DEFAULT_CSS,
                                date=date,
                                filename=os.path.basename(filename))

def write_file(path: str, content: str, overwrite: bool = False) -> None:
    if os.path.exists(path) and not overwrite:
        raise FileExistsError(f"File exists: {path} (use --overwrite to replace)")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)

def interactive_prompt(defaults):
    print("Interactive custom HTML generator (press Enter to accept default values)\n")
    filename = input(f"Output filename [{defaults['filename']}]: ").strip() or defaults['filename']
    title = input(f"Page title [{defaults['title']}]: ").strip() or defaults['title']
    heading = input(f"Top heading [{defaults['heading']}]: ").strip() or defaults['heading']
    print("Enter body text. Use blank line to separate paragraphs. End input with a single line containing only 'EOF'.")
    lines = []
    while True:
        line = input()
        if line.strip() == "EOF":
            break
        lines.append(line)
    body = "\n".join(lines).strip() or defaults['body']
    use_default_css = input("Use default CSS? (Y/n) ").strip().lower() or "y"
    css = DEFAULT_CSS
    if use_default_css.startswith("n"):
        css_path = input("Path to CSS file (leave empty for none): ").strip()
        if css_path and os.path.exists(css_path):
            with open(css_path, "r", encoding="utf-8") as cf:
                css = cf.read()
        else:
            css = ""
    return filename, title, heading, body, css

def main():
    parser = argparse.ArgumentParser(description="Generate a custom static HTML file.")
    parser.add_argument("--filename", "-o", help="Output HTML filename", default="index.html")
    parser.add_argument("--title", help="Page title", default="My Generated Page")
    parser.add_argument("--heading", help="Top heading", default="")
    parser.add_argument("--body", help="Body text (use \\n for newlines). If omitted, script becomes interactive.", default=None)
    parser.add_argument("--css-file", help="Path to a CSS file to include", default=None)
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing file")
    parser.add_argument("--open", action="store_true", help="Open the generated file in default web browser")
    args = parser.parse_args()

    filename = sanitize_filename(args.filename)
    css = DEFAULT_CSS
    if args.css_file:
        if os.path.exists(args.css_file):
            with open(args.css_file, "r", encoding="utf-8") as cf:
                css = cf.read()
        else:
            print(f"Warning: CSS file not found: {args.css_file} — using default CSS.")

    if args.body is None:
        # interactive mode
        defaults = {"filename": filename, "title": args.title, "heading": args.heading or args.title, "body": ""}
        filename, title, heading, body_text, css = interactive_prompt(defaults)
        filename = sanitize_filename(filename)
    else:
        title = args.title
        heading = args.heading or args.title
        body_text = args.body.replace("\\n", "\n")

    html = build_html(filename=filename, title=title, heading=heading, body_text=body_text, css=css)
    outpath = os.path.abspath(filename)
    try:
        write_file(outpath, html, overwrite=args.overwrite)
    except FileExistsError as e:
        print("", e)
        return

    print(f" HTML file created: {outpath}")
    if args.open:
        webbrowser.open(f"file://{outpath}")

if __name__ == "__main__":
    main()