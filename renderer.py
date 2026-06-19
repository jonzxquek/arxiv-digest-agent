import re
from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos

# --- Anthropic-inspired colour palette ---
# Coral accent — Anthropic's primary brand colour
CORAL_DARK    = (216, 90,  48)    # #D85A30 — headers, accents
CORAL_LIGHT   = (250, 236, 231)   # #FAECE7 — card backgrounds
CORAL_MID     = (240, 153, 123)   # #F0997B — decorative elements

# Grey ramp — Anthropic warm grey
GREY_900      = (44,  44,  42)    # #2C2C2A — primary text
GREY_600      = (95,  94,  90)    # #5F5E5A — secondary text
GREY_200      = (180, 178, 169)   # #B4B2A9 — dividers, muted
WHITE         = (255, 255, 255)


class DigestPDF(FPDF):

    def header(self):
        """Coral top bar — 10mm tall."""
        self.set_fill_color(*CORAL_DARK)
        self.rect(0, 0, 210, 10, "F")

    def footer(self):
        """Minimal footer with page number centred."""
        self.set_y(-12)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*GREY_200)
        self.cell(
            0, 5,
            f"ArXiv Research Digest  ·  {datetime.now().strftime('%d %B %Y')}  ·  Page {self.page_no()}",
            align="C"
        )

    def section_divider(self):
        """Thin warm grey rule between sections."""
        self.ln(3)
        self.set_draw_color(*GREY_200)
        self.set_line_width(0.2)
        self.line(
            self.l_margin,
            self.get_y(),
            210 - self.r_margin,
            self.get_y()
        )
        self.ln(5)


def parse_markdown(md: str) -> list[dict]:
    """
    Splits markdown into sections on ## headings.
    Returns list of {heading, body} dicts.
    """
    sections  = []
    parts     = re.split(r'\n(?=## )', md.strip())

    for part in parts:
        lines   = part.strip().split("\n")
        heading = re.sub(r'^#+\s*', '', lines[0]).strip()
        body    = "\n".join(lines[1:]).strip()
        sections.append({"heading": heading, "body": body})

    return sections


def safe_text(text: str) -> str:
    """
    Replaces characters fpdf2 can't encode in Helvetica.
    Covers em dash, en dash, smart quotes, ellipsis.
    """
    replacements = {
        "\u2014": "--",
        "\u2013": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2026": "...",
        "\u2022": "-",
        "\u00b7": "-",
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


def render_cover(pdf: DigestPDF, section: dict, topic: str = ""):
    """
    Cover block — large title, date, intro paragraph.
    Sits directly below the coral header bar.
    """
    pdf.ln(6)

    # Large title
    pdf.set_font("Helvetica", "B", 26)
    pdf.set_text_color(*GREY_900)
    pdf.multi_cell(0, 11, "ArXiv Research Digest", align="L")

    # Subtitle line — topic + date side by side
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GREY_600)
    date_str = datetime.now().strftime("%d %B %Y")
    subtitle = f"{topic}  ·  {date_str}" if topic else date_str
    pdf.cell(0, 6, safe_text(subtitle), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.ln(3)

    # Coral accent rule under the title block
    pdf.set_draw_color(*CORAL_DARK)
    pdf.set_line_width(0.8)
    pdf.line(
        pdf.l_margin,
        pdf.get_y(),
        pdf.l_margin + 60,
        pdf.get_y()
    )
    pdf.ln(6)

    # Intro paragraph
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GREY_900)
    pdf.multi_cell(0, 5.5, safe_text(section["body"]))
    pdf.ln(4)


def render_section_header(pdf: DigestPDF, heading: str):
    """
    Coloured background band behind the section heading text.
    Coral fill, white text, full page width.
    """
    pdf.ln(2)

    band_h = 9
    band_x = 0
    band_w = 210

    # Draw coral band across full page width
    pdf.set_fill_color(*CORAL_DARK)
    pdf.rect(band_x, pdf.get_y(), band_w, band_h, "F")

    # White heading text, positioned inside the band
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(*WHITE)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, band_h, safe_text(heading.upper()), new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="L")

    pdf.ln(4)


def render_theme_body(pdf: DigestPDF, body: str):
    """
    Renders the body of a theme section.
    Handles: italic description, paragraph text, paper bullet cards.
    """
    lines      = body.split("\n")
    para_lines = []

    def flush_paragraph():
        if para_lines:
            text = " ".join(para_lines).strip()
            if text:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(*GREY_900)
                pdf.multi_cell(0, 5.5, safe_text(text))
                pdf.ln(3)
            para_lines.clear()

    for line in lines:
        line = line.strip()
        if not line:
            flush_paragraph()
            continue

        # Italic description — *text* not **text**
        if (
            line.startswith("*") and line.endswith("*")
            and not line.startswith("**")
        ):
            flush_paragraph()
            desc = line.strip("*").strip()
            pdf.set_font("Helvetica", "I", 9)
            pdf.set_text_color(*GREY_600)
            pdf.multi_cell(0, 5, safe_text(desc))
            pdf.ln(2)

        # Paper bullet — * **Title** — description
        elif re.match(r'^[\*\-]\s+\*\*', line):
            flush_paragraph()
            render_paper_card(pdf, line)

        # Regular paragraph text — accumulate lines
        else:
            para_lines.append(line)

    flush_paragraph()
    pdf.ln(2)


def render_paper_card(pdf: DigestPDF, line: str):
    """
    Renders a paper highlight as a boxed card with coral-tinted background.
    Handles both ** and plain bold markdown variants.
    """
    # Strip bullet marker
    line = re.sub(r'^[\*\-]\s+', '', line).strip()

    # Match: **Title** — description  (em dash, en dash, or hyphen)
    bold_match = re.match(r'\*\*(.+?)\*\*\s*[\u2014\u2013\-]\s*(.*)', line)

    if bold_match:
        title       = bold_match.group(1).strip()
        description = bold_match.group(2).strip()
    else:
        # Fallback — whole line is title, no description
        title       = re.sub(r'\*\*', '', line).strip()
        description = ""

    # Card dimensions
    card_x = pdf.l_margin
    card_w = 210 - pdf.l_margin - pdf.r_margin
    card_y = pdf.get_y()

    # Estimate card height for background rect
    # Title ~5.5mm, description wrapped ~5mm per line
    desc_lines  = max(1, len(description) // 80 + 1) if description else 0
    card_h      = 5.5 + (desc_lines * 5) + 7   # padding top + bottom

    # Check if card fits on page — if not, add page
    if card_y + card_h > 270:
        pdf.add_page()
        card_y = pdf.get_y()

    # Draw coral-tinted card background
    pdf.set_fill_color(*CORAL_LIGHT)
    pdf.set_draw_color(*CORAL_MID)
    pdf.set_line_width(0.2)
    pdf.rect(card_x, card_y, card_w, card_h, "FD")

    # Left coral accent bar
    pdf.set_fill_color(*CORAL_DARK)
    pdf.rect(card_x, card_y, 2.5, card_h, "F")

    # Title text — bold, dark, indented past accent bar
    pdf.set_xy(card_x + 5, card_y + 3)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*GREY_900)

    # Truncate title if it would overflow
    if pdf.get_string_width(safe_text(title)) > card_w - 8:
        while (
            pdf.get_string_width(safe_text(title) + "...") > card_w - 8
            and len(title) > 10
        ):
            title = title[:-1]
        title = title + "..."

    pdf.cell(card_w - 6, 5.5, safe_text(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # Description text — regular, muted
    if description:
        pdf.set_x(card_x + 5)
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*GREY_600)
        pdf.multi_cell(card_w - 6, 4.5, safe_text(description))

    # Padding below card
    pdf.set_y(card_y + card_h + 3)


def render_spotlight(pdf: DigestPDF, section: dict):
    """
    Spotlight section — coral band header, then
    body text in a lightly tinted full-width box.
    """
    render_section_header(pdf, "Spotlight")

    # Tinted background for spotlight body
    body_x = pdf.l_margin
    body_w = 210 - pdf.l_margin - pdf.r_margin
    body_y = pdf.get_y()

    # Estimate height
    word_count = len(section["body"].split())
    est_lines  = max(4, word_count // 12)
    box_h      = est_lines * 5.5 + 10

    pdf.set_fill_color(*CORAL_LIGHT)
    pdf.rect(body_x, body_y, body_w, box_h, "F")

    # Body text inside box
    pdf.set_x(body_x + 4)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*GREY_900)
    pdf.set_y(body_y + 4)
    pdf.multi_cell(body_w - 6, 5.5, safe_text(section["body"]))
    pdf.ln(5)


def render_what_to_watch(pdf: DigestPDF, section: dict):
    """
    What to Watch — coral band header, italic body text.
    """
    render_section_header(pdf, "What to Watch")

    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(*GREY_900)
    pdf.multi_cell(0, 5.5, safe_text(section["body"]))
    pdf.ln(4)


def route_section(pdf: DigestPDF, section: dict):
    """Routes each section to the correct render function."""
    heading_lower = section["heading"].lower()

    if heading_lower in ("introduction", "intro"):
        # Already rendered as cover — skip
        return

    elif heading_lower == "spotlight":
        pdf.section_divider()
        render_spotlight(pdf, section)

    elif "watch" in heading_lower:
        render_what_to_watch(pdf, section)

    else:
        render_section_header(pdf, section["heading"])
        render_theme_body(pdf, section["body"])


def generate_pdf(md_path: str, pdf_path: str, topic: str = ""):
    """
    Main entry point.
    Reads markdown, parses sections, renders PDF, saves to disk.
    """
    with open(md_path, "r", encoding="utf-8") as f:
        md = f.read()

    sections = parse_markdown(md)

    pdf = DigestPDF(orientation="P", unit="mm", format="A4")
    pdf.set_margins(left=15, top=18, right=15)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    # Render cover from first section
    if sections:
        render_cover(pdf, sections[0], topic=topic)

    # Render remaining sections
    for section in sections[1:]:
        route_section(pdf, section)

    pdf.output(pdf_path)
    print(f"✅ PDF saved to {pdf_path}")


if __name__ == "__main__":
    today    = datetime.now().strftime("%Y-%m-%d")
    md_path  = f"outputs/digest_{today}.md"
    pdf_path = f"outputs/digest_{today}.pdf"
    generate_pdf(md_path, pdf_path, topic="Retrieval Augmented Generation")