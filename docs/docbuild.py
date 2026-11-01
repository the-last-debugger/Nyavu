"""
Reusable DOCX builders that enforce the Kabarak University project-paper format:
A4, 1-inch margins, Times New Roman 12 pt, 1.5 line spacing, justified body text,
automatic heading hierarchy, sequential table/figure captions, page numbers and an
auto-updating table of contents.
"""
from __future__ import annotations

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

FONT = "Times New Roman"


class Paper:
    def __init__(self, title: str = ""):
        self.doc = Document()
        self.table_no = 0
        self.figure_no = 0
        self._setup_page()
        self._setup_styles()

    # ------------------------------------------------------------------ setup
    def _setup_page(self):
        s = self.doc.sections[0]
        s.page_width, s.page_height = Cm(21.0), Cm(29.7)
        for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
            setattr(s, attr, Cm(2.54))

    def _setup_styles(self):
        st = self.doc.styles["Normal"]
        st.font.name = FONT
        st.font.size = Pt(12)
        st.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
        pf = st.paragraph_format
        pf.line_spacing = 1.5
        pf.space_after = Pt(0)
        pf.space_before = Pt(0)

        for name, size, bold, italic in (
            ("Heading 1", 14, True, False),
            ("Heading 2", 12, True, False),
            ("Heading 3", 12, True, True),
        ):
            h = self.doc.styles[name]
            h.font.name = FONT
            h.font.size = Pt(size)
            h.font.bold = bold
            h.font.italic = italic
            h.font.color.rgb = RGBColor(0, 0, 0)
            h.element.rPr.rFonts.set(qn("w:eastAsia"), FONT)
            h.paragraph_format.space_before = Pt(10 if name != "Heading 1" else 0)
            h.paragraph_format.space_after = Pt(6)
            h.paragraph_format.line_spacing = 1.5
            h.paragraph_format.keep_with_next = True

    # -------------------------------------------------------------- building
    def para(self, text: str = "", *, bold=False, italic=False, align="justify",
             size=None, space_after=6, space_before=0, line_spacing=None,
             first_indent=None):
        p = self.doc.add_paragraph()
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.space_before = Pt(space_before)
        if line_spacing:
            p.paragraph_format.line_spacing = line_spacing
        if first_indent:
            p.paragraph_format.first_line_indent = Cm(first_indent)
        p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
                       "left": WD_ALIGN_PARAGRAPH.LEFT,
                       "center": WD_ALIGN_PARAGRAPH.CENTER,
                       "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
        if text:
            r = p.add_run(text)
            r.bold, r.italic = bold, italic
            r.font.name = FONT
            if size:
                r.font.size = Pt(size)
        return p

    def rich(self, parts, *, align="justify", space_after=6, size=None):
        """parts = [(text, {'bold':True,'italic':True}), ...] for inline emphasis."""
        p = self.doc.add_paragraph()
        p.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
                       "left": WD_ALIGN_PARAGRAPH.LEFT}[align]
        p.paragraph_format.space_after = Pt(space_after)
        for text, fmt in parts:
            r = p.add_run(text)
            r.bold = fmt.get("bold", False)
            r.italic = fmt.get("italic", False)
            r.font.name = FONT
            if size:
                r.font.size = Pt(size)
        return p

    def h1(self, text: str, *, page_break=False):
        if page_break:
            self.doc.add_page_break()
        p = self.doc.add_heading(text, level=1)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        return p

    def h2(self, text: str):
        return self.doc.add_heading(text, level=2)

    def h3(self, text: str):
        return self.doc.add_heading(text, level=3)

    def bullets(self, items, *, style="List Number", size=None):
        out = []
        for it in items:
            p = self.doc.add_paragraph(style=style)
            p.paragraph_format.line_spacing = 1.5
            p.paragraph_format.space_after = Pt(3)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(it)
            r.font.name = FONT
            if size:
                r.font.size = Pt(size)
            out.append(p)
        return out

    def code_block(self, code: str, caption: str = "", *, size=8.4):
        """Monospaced, shaded code extract that stays inside the page margins."""
        if caption:
            self.caption(caption, kind="Table")
        for line in code.strip("\n").split("\n"):
            p = self.doc.add_paragraph()
            pf = p.paragraph_format
            pf.line_spacing = 1.0
            pf.space_after = Pt(0)
            pf.space_before = Pt(0)
            pf.left_indent = Cm(0.35)
            pf.right_indent = Cm(0.2)
            pPr = p._p.get_or_add_pPr()
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), "F2F4F7")
            pPr.append(shd)
            r = p.add_run(line if line else " ")
            r.font.name = "Consolas"
            r.element.rPr.rFonts.set(qn("w:eastAsia"), "Consolas")
            r.font.size = Pt(size)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(2)

    def references(self, items):
        """APA reference list: hanging indent, single-ish spacing, alphabetical order."""
        for item in sorted(items, key=lambda s: s.lower()):
            p = self.doc.add_paragraph()
            pf = p.paragraph_format
            pf.left_indent = Cm(1.27)
            pf.first_line_indent = Cm(-1.27)
            pf.line_spacing = 1.15
            pf.space_after = Pt(10)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            r = p.add_run(item)
            r.font.name = FONT
            r.font.size = Pt(11)

    def nlist(self, items, style: str = "roman", *, space_after=3, indent=1.1):
        """Manually numbered list with a hanging indent.

        Word's auto-numbering restarts are fragile across a long document, so the
        marker is written as literal text. This guarantees the numbering the marker
        reads on the page is the numbering we intended.
        """
        numerals = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII"]
        out = []
        for i, text in enumerate(items, 1):
            if style == "roman":
                label = f"{numerals[i - 1]}."
            elif style == "roman-lower":
                label = f"{numerals[i - 1].lower()}."
            elif style == "paren":
                label = f"({i})"
            else:
                label = f"{i}."
            p = self.doc.add_paragraph()
            pf = p.paragraph_format
            pf.left_indent = Cm(indent)
            pf.first_line_indent = Cm(-indent)
            pf.line_spacing = 1.5
            pf.space_after = Pt(space_after)
            pf.tab_stops.add_tab_stop(Cm(indent))
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r = p.add_run(f"{label}\t{text}")
            r.font.name = FONT
            out.append(p)
        return out

    # ----------------------------------------------------------------- table
    def caption(self, text: str, kind: str = "Table"):
        """Numbered caption using a SEQ field with a cached value.

        The cached value means the caption reads correctly in any viewer, while the
        field lets Word renumber and lets the List of Tables / Figures fields find it.
        """
        if kind == "Table":
            self.table_no += 1
            label, seq, n = "Table ", "Table", self.table_no
        else:
            self.figure_no += 1
            label, seq, n = "Figure ", "Figure", self.figure_no

        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(8)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.keep_with_next = True

        r = p.add_run(label)
        r.bold = True
        r.font.name = FONT
        r.font.size = Pt(10)

        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), f" SEQ {seq} \\* ARABIC ")
        inner = OxmlElement("w:r")
        t = OxmlElement("w:t")
        t.text = str(n)
        inner.append(t)
        fld.append(inner)
        p._p.append(fld)

        r2 = p.add_run(": " + text)
        r2.font.name = FONT
        r2.font.size = Pt(10)
        return p

    def toc_field(self, instr: str, placeholder: str):
        p = self.doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.3
        p.paragraph_format.space_after = Pt(4)
        run = p.add_run()
        begin = OxmlElement("w:fldChar")
        begin.set(qn("w:fldCharType"), "begin")
        it = OxmlElement("w:instrText")
        it.set(qn("xml:space"), "preserve")
        it.text = instr
        sep = OxmlElement("w:fldChar")
        sep.set(qn("w:fldCharType"), "separate")
        txt = OxmlElement("w:t")
        txt.text = placeholder
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        for el in (begin, it, sep, txt, end):
            run._r.append(el)
        return p

    def list_of(self, kind: str):
        """kind is 'Table' or 'Figure'."""
        plural = "TABLES" if kind == "Table" else "FIGURES"
        self.h1(f"LIST OF {plural}", page_break=True)
        self.toc_field(f'TOC \\h \\z \\c "{kind}"',
                       f"Right-click and choose Update Field to build the list of "
                       f"{kind.lower()}s.")

    def table(self, header, rows, widths=None, *, font_size=9.5,
              header_fill="D9E2F3", align_center=True):
        t = self.doc.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        t.autofit = True

        hdr = t.rows[0].cells
        for i, h in enumerate(header):
            hdr[i].text = ""
            p = hdr[i].paragraphs[0]
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(2)
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = p.add_run(h)
            r.bold = True
            r.font.size = Pt(font_size)
            r.font.name = FONT
            self._shade(hdr[i], header_fill)

        for row in rows:
            cells = t.add_row().cells
            for i, val in enumerate(row):
                cells[i].text = ""
                p = cells[i].paragraphs[0]
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_after = Pt(2)
                p.alignment = (WD_ALIGN_PARAGRAPH.CENTER if (align_center and i > 0)
                               else WD_ALIGN_PARAGRAPH.LEFT)
                r = p.add_run(str(val))
                r.font.size = Pt(font_size)
                r.font.name = FONT

        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Cm(w)

        # repeat header row across pages
        trPr = t.rows[0]._tr.get_or_add_trPr()
        el = OxmlElement("w:tblHeader")
        el.set(qn("w:val"), "true")
        trPr.append(el)
        return t

    @staticmethod
    def _shade(cell, hex_fill: str):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_fill)
        tcPr.append(shd)

    # ----------------------------------------------------------------- figure
    def figure(self, path: str, caption: str, width_cm: float = 15.0):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        p.add_run().add_picture(path, width=Cm(width_cm))
        self.caption(caption, kind="Figure")

    # ------------------------------------------------------------- utilities
    def page_numbers(self, fmt: str = "decimal", start: int = 1):
        """Footer page numbers as a real field so they update in Word."""
        for section in self.doc.sections:
            self.footer_page_numbers(section)
            self.set_page_numbering(section, fmt=fmt, start=start)

    def footer_page_numbers(self, section, size: int = 10):
        section.footer.is_linked_to_previous = False
        p = section.footer.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.0
        run = p.add_run()
        run.font.name = FONT
        run.font.size = Pt(size)
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), " PAGE ")
        inner = OxmlElement("w:r")
        rPr = OxmlElement("w:rPr")
        rf = OxmlElement("w:rFonts")
        rf.set(qn("w:ascii"), FONT)
        rPr.append(rf)
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(size * 2))
        rPr.append(sz)
        inner.append(rPr)
        t = OxmlElement("w:t")
        t.text = "1"
        inner.append(t)
        fld.append(inner)
        run._r.addnext(fld)

    @staticmethod
    def set_page_numbering(section, *, fmt: str = "decimal", start: int | None = 1):
        """fmt: 'decimal', 'lowerRoman', 'upperRoman'."""
        sectPr = section._sectPr
        pg = sectPr.find(qn("w:pgNumType"))
        if pg is None:
            pg = OxmlElement("w:pgNumType")
            sectPr.append(pg)
        pg.set(qn("w:fmt"), fmt)
        if start is not None:
            pg.set(qn("w:start"), str(start))

    def new_section(self, *, fmt: str = "decimal", start: int | None = 1):
        from docx.enum.section import WD_SECTION
        s = self.doc.add_section(WD_SECTION.NEW_PAGE)
        s.page_width, s.page_height = Cm(21.0), Cm(29.7)
        for attr in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
            setattr(s, attr, Cm(2.54))
        self.footer_page_numbers(s)
        self.set_page_numbering(s, fmt=fmt, start=start)
        return s

    def add_toc(self, levels: str = "1-3"):
        p = self.doc.add_paragraph()
        run = p.add_run()
        fld_char = OxmlElement("w:fldChar")
        fld_char.set(qn("w:fldCharType"), "begin")
        instr = OxmlElement("w:instrText")
        instr.set(qn("xml:space"), "preserve")
        instr.text = f'TOC \\o "{levels}" \\h \\z \\u'
        sep = OxmlElement("w:fldChar")
        sep.set(qn("w:fldCharType"), "separate")
        txt = OxmlElement("w:t")
        txt.text = "Right-click and choose Update Field to build the table of contents."
        end = OxmlElement("w:fldChar")
        end.set(qn("w:fldCharType"), "end")
        for el in (fld_char, instr, sep, txt, end):
            run._r.append(el)

    def update_fields_on_open(self):
        settings = self.doc.settings.element
        el = OxmlElement("w:updateFields")
        el.set(qn("w:val"), "true")
        settings.append(el)

    def save(self, path: str):
        self.doc.save(path)
        return path
