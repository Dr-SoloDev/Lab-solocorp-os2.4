# Markdown to PDF Generation

When you need to **generate** a PDF from markdown (not extract from one), use available system tools in this priority order:

## 1. pandoc (preferred, rarely installed)

```bash
pandoc input.md -o output.pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V documentclass=article \
  -V CJKmainfont="Noto Sans Thai"  # For Thai/Chinese/Japanese
```

Handles complex markdown, tables, code blocks, and international fonts cleanly.

## 2. LibreOffice headless (fallback, widely available)

```bash
libreoffice --headless --convert-to pdf input.md --outdir /tmp
```

**Pros:**
- Pre-installed on most Linux systems
- Handles basic markdown → PDF
- Works with Thai/international characters

**Cons:**
- Warning about javaldx (safe to ignore)
- Less sophisticated formatting than pandoc
- Tables and complex markdown may not render perfectly

**When to use:** When pandoc/weasyprint unavailable and you need a quick PDF export.

## 3. Python libraries (install-on-demand)

### weasyprint (HTML-first)

```bash
pip install weasyprint markdown
```

```python
import markdown
from weasyprint import HTML

with open('input.md', 'r') as f:
    html = markdown.markdown(f.read())

HTML(string=f'<html><body>{html}</body></html>').write_pdf('output.pdf')
```

Good for styled PDFs with CSS control.

### reportlab (low-level)

```bash
pip install reportlab
```

Low-level PDF generation — use only when you need programmatic control over exact layout.

## 4. wkhtmltopdf (deprecated but still around)

```bash
wkhtmltopdf input.html output.pdf
```

Qt WebKit-based. Deprecated upstream but sometimes pre-installed.

---

## Workflow: Project Summary → PDF

**Pattern from session 2026-06-08:**

1. Explore project structure
2. Read key documentation files (README, CLAUDE.md, context, decisions, ideas, project brains)
3. Consolidate into single markdown summary (`/tmp/project-summary.md`)
4. Convert to PDF using available tool (LibreOffice worked)
5. Deliver via MEDIA: path for Telegram

**Key insight:** LibreOffice headless mode is a reliable fallback when pandoc/weasyprint aren't available. The javaldx warning is cosmetic and safe to ignore.

---

## Detection

Check what's available before deciding:

```bash
which pandoc libreoffice wkhtmltopdf 2>/dev/null
python3 -c "import weasyprint" 2>&1
```

Use the first one found in priority order.
