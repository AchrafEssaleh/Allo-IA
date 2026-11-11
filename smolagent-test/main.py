
import json
import os
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape
from dotenv import load_dotenv

load_dotenv()

from smolagents import (
    OpenAIModel,
    ToolCallingAgent,
    VisitWebpageTool,
    WebSearchTool,
)
from docx import Document
from docx.shared import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    HRFlowable,
)


OUTPUT_DIR = Path("test_output")
OUTPUT_DIR.mkdir(exist_ok=True)

ILAAS_MODEL_ID = "qwen-3.6-35b-instruct"


def create_agent(model_id=ILAAS_MODEL_ID):
    """Create the documentation agent."""
    model = OpenAIModel(
        model_id=model_id,
        api_base="https://llm.ilaas.fr/v1",
        api_key=os.environ["ILAAS_API_KEY"],
        temperature=0.2,
        max_tokens=4000,
    )

    return ToolCallingAgent(
        tools=[],
        model=model,
        max_steps=8,
        instructions="""
You are an assistant that documents technical projects, especially
FabLab, electronics, fabrication, and software projects.

Your goal is to transform the user's project description into a
clear, useful, reproducible technical notebook.

Rules:
- Preserve the facts provided by the user.
- Never invent measurements, materials, steps, results, or decisions.
- Mark unknown information as "Not specified".
- You may search the web for relevant technical references when useful.
- Prefer official manuals, manufacturer documentation, and reliable sources.
- Distinguish user-provided facts from information found online.
- Do not claim that a procedure was tested unless the user says so.
- Use the same language as the project description.

Return ONLY valid JSON with this structure:
{
  "title": "Project title",
  "summary": "Short project summary",
  "sections": [
    {
      "heading": "Objectives",
      "content": "Paragraph one.\\n\\nParagraph two."
    }
  ]
}

JSON formatting rules:
- Return strictly valid JSON.
- Escape newline characters inside strings using \\n.
- Escape quotation marks inside strings.
- Do not use Markdown code fences.
- Do not include explanations before or after the JSON.

Include relevant sections such as:
Objectives, Context and problem, Materials and tools,
Technical choices, Procedure, Difficulties and solutions,
Results and tests, Possible improvements, and Missing information.

""",
    )


def parse_agent_output(raw_output):
    """Parse and validate the JSON returned by the agent."""

    text = str(raw_output).strip()

    # Remove Markdown code fences.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    # Extract the JSON object if additional text is present.
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("No JSON object found in agent output.")

    text = text[start:end + 1]

    try:
        data = json.loads(text)

    except json.JSONDecodeError as error:
        # Retry by escaping literal control characters
        # occurring inside JSON strings.
        repaired = []
        inside_string = False
        escaped = False

        for char in text:
            if escaped:
                repaired.append(char)
                escaped = False
                continue

            if char == "\\" and inside_string:
                repaired.append(char)
                escaped = True
                continue

            if char == '"':
                inside_string = not inside_string
                repaired.append(char)
                continue

            if inside_string and ord(char) < 32:
                repaired.append({
                    "\n": r"\n",
                    "\r": r"\r",
                    "\t": r"\t",
                }.get(char, " "))
            else:
                repaired.append(char)

        try:
            data = json.loads("".join(repaired))
        except json.JSONDecodeError:
            raise error

    if not isinstance(data, dict):
        raise ValueError("Agent output must be a JSON object.")

    if not isinstance(data.get("sections"), list):
        raise ValueError("Agent output has no valid 'sections' list.")

    data.setdefault("title", "Technical project notebook")
    data.setdefault("summary", "")

    return data



def create_docx(data, path):
    """Export the documentation as a Word document."""
    doc = Document()

    section = doc.sections[0]
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)

    doc.styles["Normal"].font.name = "Arial"
    doc.styles["Normal"].font.size = Pt(10)

    doc.add_heading(data["title"], level=0)
    doc.add_paragraph(data["summary"])

    for item in data["sections"]:
        doc.add_heading(item.get("heading", "Section"), level=1)
        content = item.get("content", "Not specified")

        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("- "):
                doc.add_paragraph(line[2:], style="List Bullet")
            else:
                doc.add_paragraph(line)

    doc.save(path)


def create_pdf(data, path):
    """Export the documentation as a PDF."""
    pdf = SimpleDocTemplate(
        str(path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ProjectTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        textColor=colors.HexColor("#243B53"),
        spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#334E68"),
        spaceBefore=12,
        spaceAfter=6,
    ))

    story = [
        Paragraph(escape(data["title"]), styles["ProjectTitle"]),
        Paragraph(escape(data["summary"]), styles["BodyText"]),
        Spacer(1, 12),
        HRFlowable(width="100%", thickness=0.8),
    ]

    for item in data["sections"]:
        story.append(Paragraph(
            escape(item.get("heading", "Section")),
            styles["SectionHeading"],
        ))

        content = item.get("content", "Not specified")
        for line in content.splitlines():
            line = line.strip()
            if not line:
                story.append(Spacer(1, 5))
            elif line.startswith("- "):
                story.append(Paragraph(
                    "&#8226; " + escape(line[2:]),
                    styles["BodyText"],
                ))
            else:
                story.append(Paragraph(
                    escape(line), styles["BodyText"]
                ))
                story.append(Spacer(1, 5))

    pdf.build(story)


def main():
    if len(sys.argv) < 2:
        print("Usage: python smolagent_test.py example_description.txt")
        sys.exit(1)

    description_path = Path(sys.argv[1])
    if not description_path.is_file():
        sys.exit(f"File not found: {description_path}")

    description = description_path.read_text(encoding="utf-8").strip()
    if not description:
        sys.exit("The project description is empty.")

    agent = create_agent(model_id=ILAAS_MODEL_ID)

    task = f"""
    Create a technical project notebook from the description below.

    Do not fill gaps with guesses. List important missing information
    explicitly in the documentation.

    PROJECT DESCRIPTION:
    {description}
    """

    print("Generating documentation...")
    raw_output = agent.run(task)

    data = parse_agent_output(raw_output)

    base_name = re.sub(
        r"[^a-zA-Z0-9_-]+", "_", description_path.stem
    ).strip("_") or "project"

    docx_path = OUTPUT_DIR / f"{base_name}_documentation.docx"
    pdf_path = OUTPUT_DIR / f"{base_name}_documentation.pdf"

    create_docx(data, docx_path)
    create_pdf(data, pdf_path)

    print(f"Word document: {docx_path}")
    print(f"PDF document:  {pdf_path}")


if __name__ == "__main__":
    main()
