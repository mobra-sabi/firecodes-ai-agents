#!/usr/bin/env python3
"""
Export raport în PDF
"""

from pathlib import Path
from typing import Optional


def markdown_to_pdf(md_file: Path, output_pdf: Optional[Path] = None) -> Path:
    """Convertește Markdown în PDF"""
    try:
        import markdown
        from weasyprint import HTML, CSS
    except ImportError:
        print("⚠️  weasyprint nu este instalat. Instalează cu: pip install weasyprint markdown")
        return None
    
    # Citește Markdown
    with open(md_file, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convertește în HTML
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    # Adaugă CSS pentru styling
    html_with_style = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
                line-height: 1.6;
                color: #1e293b;
                max-width: 900px;
                margin: 0 auto;
                padding: 40px;
            }}
            h1 {{
                color: #3b82f6;
                border-bottom: 3px solid #3b82f6;
                padding-bottom: 10px;
            }}
            h2 {{
                color: #6366f1;
                margin-top: 30px;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin: 20px 0;
            }}
            th, td {{
                border: 1px solid #e2e8f0;
                padding: 12px;
                text-align: left;
            }}
            th {{
                background-color: #f1f5f9;
                font-weight: bold;
            }}
            code {{
                background-color: #f1f5f9;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Generează PDF
    if output_pdf is None:
        output_pdf = md_file.parent / f"{md_file.stem}.pdf"
    
    HTML(string=html_with_style).write_pdf(output_pdf)
    return output_pdf


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python pdf_export.py <markdown_file>")
        sys.exit(1)
    
    md_file = Path(sys.argv[1])
    pdf_file = markdown_to_pdf(md_file)
    if pdf_file:
        print(f"✅ PDF generat: {pdf_file}")

