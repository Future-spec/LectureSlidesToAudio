"""Generate the LectureLens product showcase PDF."""

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "showcase" / "LectureLens_Showcase.pdf"
PAGE_W, PAGE_H = A4
INK = colors.HexColor("#18221F")
MUTED = colors.HexColor("#64706C")
PAPER = colors.HexColor("#F5F1E9")
TEAL = colors.HexColor("#0D786E")
MINT = colors.HexColor("#CCE9D9")
CORAL = colors.HexColor("#E67B5F")
LINE = colors.HexColor("#D9DDD5")
WHITE = colors.white


class Rule(Flowable):
    def __init__(self, width, color=LINE, thickness=0.8):
        super().__init__()
        self.width = width
        self.color = color
        self.thickness = thickness
        self.height = 6 * mm

    def draw(self):
        self.canv.setStrokeColor(self.color)
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, self.height / 2, self.width, self.height / 2)


def box(content, background=WHITE, padding=12, border=LINE, width=None):
    table = Table([[content]], colWidths=[width] if width else None)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.7, border),
                ("LEFTPADDING", (0, 0), (-1, -1), padding),
                ("RIGHTPADDING", (0, 0), (-1, -1), padding),
                ("TOPPADDING", (0, 0), (-1, -1), padding),
                ("BOTTOMPADDING", (0, 0), (-1, -1), padding),
            ]
        )
    )
    return table


def styles():
    base = getSampleStyleSheet()
    return {
        "eyebrow": ParagraphStyle("eyebrow", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=8, leading=11, textColor=CORAL, tracking=1.8, spaceAfter=7),
        "display": ParagraphStyle("display", parent=base["Title"], fontName="Helvetica-Bold", fontSize=36, leading=38, textColor=INK, spaceAfter=13),
        "display_teal": ParagraphStyle("display_teal", parent=base["Title"], fontName="Helvetica-Bold", fontSize=36, leading=38, textColor=TEAL, spaceAfter=13),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=25, leading=29, textColor=INK, spaceAfter=11),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=INK, spaceAfter=6),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, textColor=MUTED, spaceAfter=7),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName="Helvetica", fontSize=8.5, leading=12, textColor=MUTED),
        "white_body": ParagraphStyle("white_body", parent=base["BodyText"], fontName="Helvetica", fontSize=10.5, leading=16, textColor=colors.HexColor("#D6E7DE"), spaceAfter=7),
        "white_h": ParagraphStyle("white_h", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=WHITE, spaceAfter=8),
        "number": ParagraphStyle("number", parent=base["Normal"], fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=CORAL),
        "card_title": ParagraphStyle("card_title", parent=base["Heading3"], fontName="Helvetica-Bold", fontSize=12, leading=15, textColor=INK, spaceAfter=5),
        "center": ParagraphStyle("center", parent=base["BodyText"], fontName="Helvetica-Bold", fontSize=10, leading=14, textColor=INK, alignment=TA_CENTER),
    }


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(MUTED)
    canvas.setFont("Helvetica", 8)
    canvas.drawString(18 * mm, 12 * mm, "LECTURELENS  /  PRODUCT SHOWCASE")
    canvas.drawRightString(PAGE_W - 18 * mm, 12 * mm, f"{doc.page:02d}")
    canvas.restoreState()


def card(title, text, number=None, background=WHITE, width=82 * mm):
    s = styles()
    head = []
    if number:
        head.append(Paragraph(number, s["number"]))
    head.append(Paragraph(title, s["card_title"]))
    content = [Table([head], colWidths=[10 * mm, width - 10 * mm] if number else [width]), Paragraph(text, s["small"])]
    return box(content, background=background, width=width)


def build_story():
    s = styles()
    story = []

    story += [Spacer(1, 20 * mm), Paragraph("ACCESSIBLE LEARNING / PRODUCT SHOWCASE", s["eyebrow"]), Paragraph("Make every lecture<br/><font color='#0D786E'>audible.</font>", s["display"]), Paragraph("LectureLens transforms visual lecture material into a listening-first lesson with structure, context, and tools that help ideas stick.", s["body"]), Spacer(1, 6 * mm)]
    hero = Table([[Paragraph("SLIDE", s["center"]), Paragraph("AI-GUIDED", s["center"]), Paragraph("LEARN", s["center"])]], colWidths=[49 * mm] * 3)
    hero.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), MINT), ("BACKGROUND", (1, 0), (1, 0), TEAL), ("BACKGROUND", (2, 0), (2, 0), CORAL), ("TEXTCOLOR", (1, 0), (1, 0), WHITE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.7, PAPER), ("TOPPADDING", (0, 0), (-1, -1), 16), ("BOTTOMPADDING", (0, 0), (-1, -1), 16)]))
    story += [hero, Spacer(1, 9 * mm), Paragraph("A focused companion for students who learn better by listening, revisiting, and asking one more question.", s["small"]), PageBreak()]

    story += [Paragraph("01 / THE EXPERIENCE", s["eyebrow"]), Paragraph("From slide to study session in one calm flow.", s["h1"]), Paragraph("The product keeps the learner in motion: bring material, choose the level of explanation, then move between listening, reading, practice, and questions without losing the source.", s["body"]), Spacer(1, 4 * mm)]
    flow = [[card("Bring the material", "Upload a PDF or slide image, or paste source text directly.", "01", MINT, 54 * mm), card("Find the meaning", "Extract structure, create a natural explanation, and surface key points.", "02", colors.HexColor("#FDF8F2"), 54 * mm), card("Keep learning", "Listen, replay, quiz yourself, open flashcards, and ask the lesson tutor.", "03", colors.HexColor("#EAF2EE"), 54 * mm)]]
    table = Table(flow, colWidths=[56 * mm, 56 * mm, 56 * mm], hAlign="LEFT")
    table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    story += [table, Spacer(1, 12 * mm), Rule(170 * mm), Paragraph("What makes the experience feel complete", s["h2"])]
    features = [[Paragraph("<b>Listening-first narration</b><br/>Paragraph-level playback, voice selection, speed control, and resume progress.", s["small"]), Paragraph("<b>Deck intelligence</b><br/>Structured slide map with independent playback for each slide in a PDF.", s["small"])], [Paragraph("<b>Study kit</b><br/>Summary, quick quiz, flashcards, next steps, and interactive scoring.", s["small"]), Paragraph("<b>Grounded tutor</b><br/>Follow-up answers stay constrained to the current lesson source.", s["small"])]]
    ft = Table(features, colWidths=[82 * mm, 82 * mm], rowHeights=[25 * mm, 25 * mm])
    ft.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.7, LINE), ("BACKGROUND", (0, 0), (-1, -1), WHITE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("TOPPADDING", (0, 0), (-1, -1), 10)]))
    story += [ft, PageBreak()]

    story += [Paragraph("02 / A REAL DEMO STORY", s["eyebrow"]), Paragraph("Photosynthesis, heard three ways.", s["h1"]), Paragraph("The built-in offline demo now shows the product's strongest promise: one concept becomes a small, navigable lesson rather than a flat transcript.", s["body"])]
    slides = [[Paragraph("01", s["number"]), Paragraph("THE BIG IDEA<br/><font color='#64706C'>Plants turn light energy into stored chemical energy.</font>", s["body"]), Paragraph("PLAY", s["center"])], [Paragraph("02", s["number"]), Paragraph("INPUTS AND OUTPUTS<br/><font color='#64706C'>Sunlight, carbon dioxide, and water become glucose and oxygen.</font>", s["body"]), Paragraph("PLAY", s["center"])], [Paragraph("03", s["number"]), Paragraph("THE EQUATION<br/><font color='#64706C'>6CO2 + 6H2O -> C6H12O6 + 6O2</font>", s["body"]), Paragraph("PLAY", s["center"])]]
    slide_table = Table(slides, colWidths=[17 * mm, 125 * mm, 25 * mm], rowHeights=[24 * mm] * 3)
    slide_table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), WHITE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.7, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 11), ("RIGHTPADDING", (0, 0), (-1, -1), 11), ("TEXTCOLOR", (2, 0), (2, -1), TEAL)]))
    story += [slide_table, Spacer(1, 12 * mm)]
    dark = Table([[Paragraph("THE LEARNER GETS", s["eyebrow"]), Paragraph("A guided narration, a source transcript, key takeaways, a study kit, a deck map, replayable paragraphs, and a tutor that can explain the detail that did not land the first time.", s["white_body"])]], colWidths=[42 * mm, 120 * mm])
    dark.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), INK), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 14), ("RIGHTPADDING", (0, 0), (-1, -1), 14), ("TOPPADDING", (0, 0), (-1, -1), 14), ("BOTTOMPADDING", (0, 0), (-1, -1), 14)]))
    story += [dark, PageBreak()]

    story += [Paragraph("03 / WHY IT CAN GROW", s["eyebrow"]), Paragraph("A strong prototype with a clear next horizon.", s["h1"]), Paragraph("LectureLens already demonstrates the core learning loop locally and in a serverless-friendly Flask app. Its next stage is operational depth, not a change of direction.", s["body"]), Spacer(1, 4 * mm)]
    architecture = [[Paragraph("BROWSER", s["center"]), Paragraph("FLASK API", s["center"]), Paragraph("OPTIONAL AI", s["center"])], [Paragraph("Uploads, Web Speech playback, local history, quiz state", s["small"]), Paragraph("PDF extraction, OCR/vision handoff, narration, study kit, tutor", s["small"]), Paragraph("OpenAI-compatible narration and structured coaching", s["small"])]]
    arch = Table(architecture, colWidths=[55 * mm] * 3)
    arch.setStyle(TableStyle([("BACKGROUND", (0, 0), (0, 0), MINT), ("BACKGROUND", (1, 0), (1, 0), TEAL), ("BACKGROUND", (2, 0), (2, 0), CORAL), ("TEXTCOLOR", (1, 0), (1, 0), WHITE), ("TEXTCOLOR", (2, 0), (2, 0), WHITE), ("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.7, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 12), ("BOTTOMPADDING", (0, 0), (-1, -1), 12), ("LEFTPADDING", (0, 0), (-1, -1), 10)]))
    story += [arch, Spacer(1, 12 * mm), Paragraph("The next product moves", s["h2"])]
    roadmap = [[Paragraph("NOW", s["number"]), Paragraph("Polish the guided demo and validate the multi-slide learning flow.", s["body"])], [Paragraph("NEXT", s["number"]), Paragraph("Add accounts, persistent lesson storage, background processing for long decks, and downloadable browser audio.", s["body"])], [Paragraph("NORTH STAR", s["number"]), Paragraph("Make every lecture format feel like a personal, accessible study session that remembers where the learner left off.", s["body"])]]
    road = Table(roadmap, colWidths=[25 * mm, 140 * mm], rowHeights=[22 * mm] * 3)
    road.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.7, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.7, LINE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 12), ("RIGHTPADDING", (0, 0), (-1, -1), 12), ("BACKGROUND", (0, 0), (-1, -1), WHITE)]))
    story += [road, Spacer(1, 14 * mm), Paragraph("LectureLens", s["display_teal"]), Paragraph("Making visual learning audible, one lecture at a time.", s["body"]), Paragraph("Built with Flask, PyMuPDF, optional OpenAI-compatible services, and the device's own speech engine.", s["small"])]
    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document = BaseDocTemplate(str(OUTPUT), pagesize=A4, rightMargin=18 * mm, leftMargin=18 * mm, topMargin=16 * mm, bottomMargin=20 * mm, title="LectureLens Product Showcase", author="LectureLens")
    frame = Frame(document.leftMargin, document.bottomMargin, document.width, document.height, id="main")
    document.addPageTemplates([PageTemplate(id="showcase", frames=frame, onPage=footer)])
    document.build(build_story())
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()