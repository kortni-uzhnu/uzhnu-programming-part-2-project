"""Build the explanatory note. Requires Python 3 and ReportLab."""
from pathlib import Path
import json
import textwrap
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Flowable, Frame, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Preformatted, Spacer, Table, TableStyle,
)
from reportlab.platypus.tableofcontents import TableOfContents

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
RESULTS = json.loads((DOCS / 'test_results.json').read_text(encoding='utf-8'))
LINUX = json.loads((DOCS / 'test_results_linux.json').read_text(encoding='utf-8'))
assert RESULTS['cli_cases_passed'] == LINUX['cli_cases_passed'] == 36
assert all(row['status'] == 'PASS' for row in RESULTS['results'] + LINUX['results'])


def fonts():
    candidates = [
        (Path('C:/Windows/Fonts'), ('times.ttf', 'timesbd.ttf', 'timesi.ttf', 'consola.ttf')),
        (Path('/usr/share/fonts/truetype/dejavu'),
         ('DejaVuSerif.ttf', 'DejaVuSerif-Bold.ttf', 'DejaVuSerif-Italic.ttf', 'DejaVuSansMono.ttf')),
    ]
    for folder, names in candidates:
        if all((folder / name).exists() for name in names):
            for alias, name in zip(('Body', 'BodyBold', 'BodyItalic', 'Code'), names):
                pdfmetrics.registerFont(TTFont(alias, str(folder / name)))
            pdfmetrics.registerFontFamily('Body', normal='Body', bold='BodyBold', italic='BodyItalic')
            return
    raise RuntimeError('Install Times New Roman and Consolas, or DejaVu fonts, to rebuild the report.')


fonts()
styles = getSampleStyleSheet()
styles.add(ParagraphStyle('Text', fontName='Body', fontSize=12, leading=16,
                          alignment=TA_JUSTIFY, spaceAfter=8))
styles.add(ParagraphStyle('TitleText', fontName='BodyBold', fontSize=17, leading=22,
                          alignment=TA_CENTER, spaceAfter=14))
styles.add(ParagraphStyle('Centered', fontName='Body', fontSize=12, leading=17,
                          alignment=TA_CENTER, spaceAfter=9))
styles.add(ParagraphStyle('H1', fontName='BodyBold', fontSize=14, leading=18, spaceAfter=13,
                          keepWithNext=True))
styles.add(ParagraphStyle('H2', fontName='BodyBold', fontSize=12, leading=16, spaceBefore=8,
                          spaceAfter=9, keepWithNext=True))
styles.add(ParagraphStyle('FileHeading', fontName='BodyBold', fontSize=12, leading=16,
                          spaceBefore=8, spaceAfter=9, keepWithNext=True))
styles.add(ParagraphStyle('SmallText', fontName='Body', fontSize=10, leading=13, spaceAfter=6))
styles.add(ParagraphStyle('Cell', fontName='Body', fontSize=10.2, leading=13))
styles.add(ParagraphStyle('Caption', fontName='BodyItalic', fontSize=10.5, leading=13,
                          alignment=TA_CENTER, spaceBefore=7, spaceAfter=11))
styles.add(ParagraphStyle('Listing', fontName='Code', fontSize=7.5, leading=9.8, spaceAfter=6))
styles.add(ParagraphStyle('Terminal', fontName='Code', fontSize=9, leading=12,
                          textColor=colors.HexColor('#17212b'), backColor=colors.HexColor('#f1f3f5'),
                          borderPadding=9, spaceBefore=6, spaceAfter=12))


class Report(BaseDocTemplate):
    def afterFlowable(self, flowable):
        if isinstance(flowable, Paragraph) and flowable.style.name in ('H1', 'H2'):
            level = 0 if flowable.style.name == 'H1' else 1
            title = flowable.getPlainText()
            if title == 'Contents':
                return
            key = 'heading-' + str(self.seq.nextf('heading'))
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=level, closed=False)
            self.notify('TOCEntry', (level, title, self.page, key))


def decorate(canvas, doc):
    if doc.page == 1:
        return
    canvas.saveState()
    canvas.setFont('Body', 9)
    canvas.setFillColor(colors.HexColor('#555555'))
    canvas.drawString(25 * mm, A4[1] - 14 * mm, 'Programming, part 2 | School Students Database')
    canvas.setStrokeColor(colors.HexColor('#bbbbbb'))
    canvas.line(25 * mm, A4[1] - 16 * mm, A4[0] - 20 * mm, A4[1] - 16 * mm)
    canvas.drawCentredString(A4[0] / 2, 12 * mm, str(doc.page))
    canvas.restoreState()


class Diagram(Flowable):
    def __init__(self, mode):
        Flowable.__init__(self)
        self.mode = mode
        self.width = 460
        self.height = {'architecture': 280, 'main': 420, 'edit': 450}[mode]

    def draw(self):
        c = self.canv
        c.setStrokeColor(colors.HexColor('#253746'))
        c.setLineWidth(0.9)

        def label(x, y, text):
            lines = text.split('\n')
            c.setFillColor(colors.black)
            c.setFont('Body', 10)
            for i, line in enumerate(lines):
                c.drawCentredString(x, y + (len(lines) - 1) * 6 - i * 12 - 3, line)

        def box(x, y, w, h, text, rounded=False):
            c.setFillColor(colors.HexColor('#f5f7f8'))
            c.roundRect(x, y, w, h, 10 if rounded else 0, fill=1, stroke=1)
            label(x + w / 2, y + h / 2, text)

        def diamond(x, y, w, h, text):
            p = c.beginPath()
            p.moveTo(x, y + h / 2)
            p.lineTo(x + w / 2, y + h)
            p.lineTo(x + w, y + h / 2)
            p.lineTo(x + w / 2, y)
            p.close()
            c.setFillColor(colors.HexColor('#ffffff'))
            c.drawPath(p, fill=1, stroke=1)
            label(x + w / 2, y + h / 2, text)

        def arrow(points, text=None, offset=(0, 0)):
            p = c.beginPath()
            p.moveTo(*points[0])
            for point in points[1:]:
                p.lineTo(*point)
            c.drawPath(p)
            (x0, y0), (x, y) = points[-2:]
            if abs(x - x0) > abs(y - y0):
                sign = 1 if x > x0 else -1
                c.line(x, y, x - sign * 5, y - 3)
                c.line(x, y, x - sign * 5, y + 3)
            else:
                sign = 1 if y > y0 else -1
                c.line(x, y, x - 3, y - sign * 5)
                c.line(x, y, x + 3, y - sign * 5)
            if text:
                c.setFont('Body', 9)
                c.drawString(points[0][0] + offset[0], points[0][1] + offset[1], text)

        if self.mode == 'architecture':
            box(130, 230, 200, 44, 'main.cpp\nStartup and fatal errors')
            box(130, 155, 200, 44, 'console.cpp\nMenu, prompts and confirmation')
            box(130, 80, 200, 44, 'database.cpp\nValidation, operations and storage')
            box(0, 0, 205, 45, 'Memory\nvector<Group> / vector<Student>')
            box(255, 0, 205, 45, 'Text file\nVersioned records and next ID')
            arrow([(230, 230), (230, 199)])
            arrow([(230, 155), (230, 124)])
            arrow([(180, 80), (180, 60), (102, 60), (102, 45)])
            arrow([(280, 80), (280, 60), (357, 60), (357, 45)])
        elif self.mode == 'main':
            box(145, 380, 170, 34, 'Start', True)
            box(135, 315, 190, 43, 'Load and validate file')
            box(135, 248, 190, 43, 'Display menu and read choice')
            diamond(150, 165, 160, 62, 'Exit / end of input?')
            box(125, 92, 210, 45, 'Display data or perform operation')
            box(125, 15, 210, 45, 'Report result\nReturn to menu')
            box(355, 179, 100, 34, 'End', True)
            box(0, 319, 95, 34, 'Stop with error', True)
            arrow([(230, 380), (230, 358)])
            arrow([(230, 315), (230, 291)])
            arrow([(135, 336), (95, 336)], 'Invalid file', (-96, 33))
            arrow([(230, 248), (230, 227)])
            arrow([(310, 196), (355, 196)], 'Yes', (9, 8))
            arrow([(230, 165), (230, 137)], 'No', (8, -15))
            arrow([(230, 92), (230, 60)])
            arrow([(125, 37), (105, 37), (105, 270), (135, 270)])
        else:
            box(125, 408, 210, 35, 'Select group and student ID')
            box(125, 341, 210, 43, 'Collect all new values\nBlank means keep current value')
            box(125, 275, 210, 43, 'Copy state and apply change\nKeep ID; move group if requested')
            diamond(150, 191, 160, 62, 'Valid candidate?')
            box(125, 115, 210, 44, 'Write temporary file\nReplace main file using backup')
            diamond(150, 31, 160, 62, 'Save succeeded?')
            box(350, 203, 110, 38, 'Report error\nKeep old state')
            box(0, 42, 120, 40, 'Publish new state\nReturn to menu')
            arrow([(230, 408), (230, 384)])
            arrow([(230, 341), (230, 318)])
            arrow([(230, 275), (230, 253)])
            arrow([(310, 222), (350, 222)], 'No', (9, 8))
            arrow([(230, 191), (230, 159)], 'Yes', (9, -18))
            arrow([(230, 115), (230, 93)])
            arrow([(310, 62), (405, 62), (405, 203)], 'No', (12, 9))
            arrow([(150, 62), (120, 62)], 'Yes', (-26, 9))


story = []


def p(text, style='Text'):
    story.append(Paragraph(text, styles[style]))


def h(text, level=1):
    p(text, 'H1' if level == 1 else 'H2')


def new():
    story.append(PageBreak())


def table(headers, rows, widths):
    data = [[Paragraph('<b>' + escape(cell) + '</b>', styles['Cell']) for cell in headers]]
    data += [[Paragraph(escape(str(cell)).replace('\n', '<br/>'), styles['Cell']) for cell in row]
             for row in rows]
    result = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    result.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e8edf0')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#a9b0b5')),
        ('INNERGRID', (0, 0), (-1, -1), 0.35, colors.HexColor('#c5c9cc')),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.append(result)
    story.append(Spacer(1, 9))


def terminal(text, caption=None):
    wrapped = []
    for line in text.splitlines():
        wrapped.extend(textwrap.wrap(line, width=83, subsequent_indent='  ',
                                     replace_whitespace=False, drop_whitespace=False) or [''])
    story.append(Preformatted('\n'.join(wrapped), styles['Terminal']))
    if caption:
        p(caption, 'Caption')


def excerpt(session, start, end):
    text = RESULTS['console_sessions'][session]['stdout']
    begin = text.index(start)
    return text[begin:text.index(end, begin)].strip()


p('MINISTRY OF EDUCATION AND SCIENCE OF UKRAINE', 'Centered')
p('STATE HIGHER EDUCATIONAL INSTITUTION<br/>"UZHHOROD NATIONAL UNIVERSITY"', 'Centered')
p('FACULTY OF ENGINEERING AND TECHNOLOGY<br/>DEPARTMENT OF COMPUTER SYSTEMS AND NETWORKS', 'Centered')
story.append(Spacer(1, 38 * mm))
p('COURSE WORK', 'TitleText')
p('in the discipline "Programming, part 2"', 'Centered')
p('Software application for<br/>School Students Database', 'TitleText')
p('Explanatory note', 'Centered')
story.append(Spacer(1, 23 * mm))
p('Student: Кортні Шілдс Скаллі', 'Centered')
p('Supervisor: Assistant Hedeon T. S.', 'Centered')
story.append(Spacer(1, 12 * mm))
p('National scale ____________________<br/>Points ____________ ECTS grade ____________', 'Centered')
story.append(Spacer(1, 22 * mm))
p('Uzhhorod - 2026', 'Centered')
new()

h('Individual terms of reference')
p('<b>Topic.</b> Software application for School Students Database.')
p('<b>Goal.</b> Develop a console application in C++ that stores groups and their students, '
  'allows records to be maintained, and preserves completed changes between sessions.')
p('The project uses the Student Database topic selected for this coursework. The explanatory '
  'note example supplied in Moodle provides the report structure [1]. Editing is included '
  'as a working operation for both groups and students.')
table(['Requirement', 'Expected result'], [
    ('Structured records', 'A Group has a code, year and collection of students. A Student has a stable ID, name, birth date, average score and phone.'),
    ('Create and display', 'Create groups, add students to existing groups, list groups and display all student details.'),
    ('Edit', 'Change group code/year and every editable student field. Move a student to another group while keeping the ID.'),
    ('Delete', 'Delete a student or a group after confirmation. Deleting a group removes its students.'),
    ('Persistence', 'Save every successful modification and load the saved records at startup.'),
    ('Validation', 'Reject invalid fields, missing selections and duplicate group codes. Report errors without accepting a partial operation.'),
    ('Verification', 'Compile the project and test the database and console workflows, including saving, loading and editing.'),
], [113, 355])
p('Deliverables are the complete source project and this PDF report. The Project assignment '
  'requests a GitHub repository link [2]. The Explanatory note assignment accepts one PDF '
  'up to 5 MB [1].')
p('Student signature ____________________<br/>Supervisor signature ____________________', 'SmallText')
new()

h('Calendar plan')
p('The implementation and verification were completed on 21 November 2026. This plan '
  'records the work carried out for this version, rather than repeating the historical '
  'dates from the example.')
table(['Stage', 'Date', 'Result'], [
    ('Review Moodle instructions and the example', '21 Nov 2026', 'Scope and report structure identified'),
    ('Choose topic and define requirements', '21 Nov 2026', 'Student Database, including editing'),
    ('Choose structures and storage format', '21 Nov 2026', 'Groups, student IDs and versioned text records'),
    ('Implement the database and console', '21 Nov 2026', 'All eight menu operations implemented'),
    ('Compile and test', '21 Nov 2026', 'Windows and Linux builds; database and console suites'),
    ('Prepare the explanatory note', '21 Nov 2026', 'Report, diagrams, captured output and source listing'),
    ('Review and upload', 'Pending', 'Local files prepared for review before upload'),
    ('Presentation or defence', 'To be arranged', 'No defence date is specified on the assignment pages'),
], [219, 81, 168])
p('Both Moodle assignments list 30 June 2026 at 00:00 as the original deadline. The '
  'completion date above does not change that deadline or imply an extension.')
p('Student signature ____________________<br/>Supervisor signature ____________________', 'SmallText')
new()

h('Abstract')
p('Studbook is a local console application for managing school student records in groups. '
  'The program is written in C++17 and uses only the standard library. Groups and students '
  'are represented by structures stored in vectors. A Database class controls changes '
  'and text-file persistence, while a separate console module handles interaction.')
p('The application supports adding, displaying, editing and deleting records. A student '
  'can be moved between groups without changing the assigned ID. Input is checked before '
  'a change is accepted. Completed changes are written immediately, and saved records '
  'are restored at the next startup. The file format preserves full-precision scores, '
  'quoted names and the next available student ID.')
p('The project was compiled for Windows and Linux with strict warnings treated as '
  'errors. On each platform, 132 direct database checks and 36 end-to-end console cases '
  'passed. Tests include editing, duplicate names, group transfers, date and score '
  'boundaries, malformed files, save failures and interrupted input.')
p('The report explains the requirements, design choices, algorithms, interface and '
  'verification results. The appendices contain an editing flowchart, the complete '
  'application source listing and a test-case register.')
p('<b>Keywords:</b> C++, student records, groups, vectors, validation, editing, file storage, console application.')
new()

p('Contents', 'H1')
toc = TableOfContents()
toc.levelStyles = [
    ParagraphStyle('TOC0', fontName='Body', fontSize=10.5, leading=13, spaceBefore=4),
    ParagraphStyle('TOC1', fontName='Body', fontSize=9.5, leading=12, leftIndent=13, spaceBefore=2),
]
story.append(toc)
new()

h('Introduction')
p('Student records are useful only when they can be kept consistent as details change. '
  'A teacher may need to correct a name, update a phone number, move a student to another '
  'group or remove an old record. The purpose of this coursework is to implement those '
  'ordinary tasks in a small program whose data structures and behaviour can be inspected.')
p('The selected topic is a School Students Database. In this project, the word database '
  'means an organised collection stored in memory and a text file. No database server '
  'is installed. This keeps attention on structures, collections, functions, input '
  'validation and file operations, which are the main programming tasks.')
p('The example supplied with the assignment describes a console student-group manager. '
  'Its terms of reference require creating, editing and deleting records, saving progress '
  'and loading saved groups [1]. Studbook follows those requirements and provides actual '
  'editing operations. The report describes this implementation and its observed results.')
p('The scope is deliberately local and single-user. One instance opens one data file, '
  'presents a menu and saves completed modifications. The program does not provide '
  'network access, user accounts or a graphical interface. A teacher using a production '
  'system would need additional controls for privacy, concurrent access and backups.')
p('The work has three practical outcomes. First, the program maintains the relationship '
  'between groups and students. Second, incorrect input or a failed write must not be '
  'reported as a successful change. Third, the design must be simple enough to explain '
  'through its source code, flowcharts and repeatable tests.')
p('The following sections set out the requirements, compare possible approaches and '
  'explain the chosen algorithms. The development section then connects the source '
  'modules to the user interface, storage format and test evidence.')
new()

h('1 Analysis of the terms of reference')
p('A group is the main organisational unit. It has a unique, case-sensitive code and a '
  'year. Each group contains zero or more students. Every student has a name, birth '
  'date, average score and phone number. The program adds a numeric ID so that two '
  'students with the same name can still be edited and deleted separately.')
p('Creating a group requires a new code and valid year. Adding a student requires an '
  'existing group. Displaying groups shows their codes, years and student counts. '
  'Displaying a group lists each student ID and all stored fields.')
p('Editing a group changes its code and year without detaching its students. Editing a '
  'student can change all four personal fields and the associated group. The ID is kept. '
  'Blank responses during editing retain the existing values. A duplicate group code '
  'or invalid destination group rejects the entire edit.')
p('Deletion is confirmed before the database operation is called. Removing a group '
  'also removes the students stored inside it, and the prompt states that count. '
  'Removing a student affects only the selected ID. A response other than YES cancels '
  'either deletion.')
table(['Acceptance condition', 'How it is checked'], [
    ('Every completed change survives a restart', 'Reload the same file in another process and compare records'),
    ('Editing changes the intended record only', 'Use stable IDs, duplicate names and cross-group moves in tests'),
    ('Invalid actions preserve existing records', 'Compare the data file before and after rejected operations'),
    ('Bad files do not become empty databases', 'Refuse startup and leave the source bytes unchanged'),
    ('The project can be built without extra C++ libraries', 'Compile all modules as C++17 on Windows and Linux'),
], [227, 241])
p('The bounds on group codes, years, names, phone numbers and collection sizes are '
  'project design choices. They make validation explicit rather than adding requirements '
  'that Moodle did not state. Detailed limits appear in section 4.4.')
new()

h('2 Analysis of existing methods and approaches')
p('Several approaches could represent the same records. A fixed-size array is easy to '
  'understand but requires an arbitrary capacity or manual reallocation. A vector '
  'provides a resizable sequence with automatic ownership [3]. Nested vectors match '
  'the relationship between a group and its students without a separate relationship table.')
p('A map indexed by group code could make lookup faster. For this small teaching '
  'project, linear lookup keeps the implementation shorter and preserves insertion '
  'order. Student IDs provide unambiguous selection without requiring names to be unique. '
  'Sets are used temporarily to validate that codes and IDs are not duplicated.')
table(['Approach', 'Advantages', 'Reason for this project'], [
    ('Vectors and structures', 'Clear ownership, flexible size, standard library', 'Selected for the in-memory model'),
    ('Plain text file', 'Readable, easy to inspect and demonstrate', 'Selected with a version header and strict record checks'),
    ('SQLite database', 'Queries and transactions', 'Useful for a larger system; adds an external library and more setup'),
    ('JSON or XML', 'Common interchange formats', 'A parser would add code or dependencies without helping the required operations'),
    ('Graphical or web interface', 'Visual forms and richer interaction', 'Outside the selected console application scope'),
], [107, 163, 198])
p('A line-based text format was selected because it can be examined directly during '
  'testing. Standard file streams handle input and output [4]. Quoted text fields '
  'escape quotes and backslashes [5], avoiding a special restriction on ordinary names.')
p('The main trade-off is that a successful modification copies and rewrites the '
  'collection. That is acceptable for the small local records used here. A larger or '
  'multi-user application would benefit from indexed storage, locking and database '
  'transactions. This implementation does not claim those facilities.')
new()

h('3 Selected methods and algorithms')
p('The main loop repeatedly displays a numbered menu, reads a complete line and '
  'dispatches the selected operation. Numeric parsing requires the whole response to '
  'be a valid number. For example, 3x is rejected instead of being accepted as option 3. '
  'Invalid entries produce an error and return to the menu.')
p('Group lookup scans the group vector for an exact code. Student lookup scans the '
  'selected group for an ID. Display operations iterate over the corresponding '
  'vectors. No recursive data structure is used, so iteration is sufficient.')
p('Modification uses a candidate copy of the current collection. The operation is '
  'applied to that copy, the complete state is validated, and the candidate is saved. '
  'Only a successful file replacement publishes the candidate as the new in-memory '
  'state. Rejected validation and ordinary write failures therefore leave the old '
  'in-memory records available.')
p('Student IDs are assigned from a counter stored in the file. Adding a student '
  'increments it; editing and moving a student preserve the existing ID. Deletion '
  'does not decrement the counter. This prevents an old deleted ID from being reassigned '
  'after a restart. Addition stops if the integer ID range is exhausted.')
p('Loading reads the format header, next-ID record, group count, and the declared '
  'number of students in each group. A temporary collection is validated before '
  'replacing the existing state. Counts, field values, duplicate identifiers and '
  'unexpected trailing records are checked. Resource limits prevent an invalid file '
  'from requesting an unbounded number of records.')
table(['Operation', 'Cost and reason'], [
    ('Find a group / student', 'O(G) / O(Sg), using a linear scan'),
    ('Display groups / all students', 'O(G) / O(S), visiting each displayed record'),
    ('Check uniqueness', 'O(G log G + S log S), using sets'),
    ('Accept a modification', 'Copy O(G + S), validate, then write the complete file'),
    ('Memory', 'O(G + S) for records, plus a candidate copy during a change'),
], [169, 299])
p('G is the group count, Sg is the selected group size, and S is the total student '
  'count. These bounds explain why the design is appropriate for a small local application.')
new()

h('4 Program development')
h('4.1 Data structures and architecture', 2)
p('The Student structure contains an integer ID, three text fields and a double '
  'score. The Group structure contains its code, year and vector of Student objects. '
  'Student counts are derived from vector sizes, avoiding a separate count that could '
  'fall out of sync when a record is added, deleted or moved.')
terminal('Student: id, name, birthDate, averageScore, phone\n'
         'Group:   code, year, vector<Student> students\n'
         'Database: filename_, vector<Group> groups_, nextId_')
story.append(Diagram('architecture'))
p('Figure 4.1 - Source modules and the two representations of the records.', 'Caption')
p('Database exposes read-only access to its collections. Console code cannot directly '
  'modify a vector. All accepted changes pass through the validation and persistence '
  'path. The console receives streams as arguments, making the same interface usable '
  'with a terminal or scripted test input.')
new()

h('4.2 Source modules and responsibilities', 2)
table(['File', 'Responsibility'], [
    ('database.hpp', 'Student and Group structures, validation declarations and the public Database interface'),
    ('database.cpp', 'Field validation, lookups, CRUD operations, loading and staged file replacement'),
    ('console.hpp', 'Declaration of runConsole(Database&, istream&, ostream&)'),
    ('console.cpp', 'Menu dispatch, full-line input, edit defaults, displays and deletion confirmation'),
    ('main.cpp', 'Command-line filename, startup loading and fatal error reporting'),
    ('database_tests.cpp', '132 direct checks of fields, operations, round trips and rejected files'),
    ('cli_tests.py', '36 end-to-end cases run against a compiled executable'),
], [124, 344])
p('The Database public operations are addGroup, editGroup, deleteGroup, addStudent, '
  'editStudent and deleteStudent. Every successful modification calls commit. '
  'That function checks the candidate, saves it, then swaps it into memory.')
p('The group and student accessors return const references for display and selection. '
  'Where an edit needs several prompts, the console first copies the selected record. '
  'No reference into a modified vector is kept across a commit.')
p('main accepts zero or one filename argument. Without a filename it uses '
  'students_data.txt in the current working directory. --help prints usage. Too many '
  'arguments or an unreadable database produce a nonzero exit status. The console '
  'returns normally on option 0 or the end of input.')
p('Only standard C++17 headers are required. The project includes a CMake description '
  'as an optional build route, but a single compiler command can build the program. '
  'Python is needed only for the optional console test script and report regeneration.')
new()

h('4.3 Control flow and saving', 2)
story.append(Diagram('main'))
p('Figure 4.2 - Startup validation and the console loop. Modification details are in Appendix A.', 'Caption')
p('A missing data file starts a new empty database. An existing malformed file is '
  'an error, so the program stops before the menu. A valid file restores groups, '
  'students and the next ID. Display operations do not save anything.')
p('For an operation error the console prints the reason and returns to the menu. '
  'All input for an edit is collected before commit. End-of-input during prompts '
  'cancels the incomplete operation. Earlier completed operations are already saved, '
  'so exiting requires no additional write.')
new()

h('4.4 User interface and instructions', 2)
p('Start the program from a terminal. The first lines state how many groups and '
  'students were loaded. Enter a menu number and then one response per prompt. '
  'Text entered at the console does not need quotes.')
first_output = RESULTS['console_sessions']['Add groups and students']['stdout']
terminal(first_output[:first_output.index('Choice:') + len('Choice:')],
         'Figure 4.3 - Actual menu output from the Windows console test run.')
p('Add a group before adding its students. For example, choose 1, enter CE-101 '
  'and year 2026. Choose 2 to select that group and supply a name, date, score and '
  'phone. The confirmation includes the assigned student ID.')
terminal(excerpt('Add groups and students', 'Groups: 2 | Students: 2', '\n1. Add group'),
         'Figure 4.4 - Group counts after adding two students.')
p('Option 4 asks for a group code and lists all fields for each student. Options '
  '7 and 8 show what will be removed and require the exact word YES. Other responses '
  'cancel deletion. Deleting a nonempty group removes all of its students.')
new()

p('Editing records', 'H2')
p('Option 5 edits a group. Enter the current code, then the replacement code and '
  'year. Blank responses keep the current values. Renaming the group preserves its '
  'student list, and a code already used by another group is rejected.')
p('Option 6 displays the students of a group and asks for the student ID. It then '
  'offers the destination group, name, birth date, score and phone, showing current '
  'values in brackets. The ID is not editable. Enter another existing group code '
  'to transfer the student, or leave it blank to keep the current group.')
terminal('Test input for the edit example:\n'
         '6\nCE-201\n1\nCE-102\nAlex Morgan-Reed\n2008-03-01\n95.25\n+380 50 111 2233')
terminal(excerpt('Edit every student field and move group', 'Group: CE-102 | Students: 1', '\n1. Add group'),
         'Figure 4.5 - Actual output after changing all fields and moving student ID 1.')
p('The source group then contains one fewer student, and the destination contains '
  'one more. A test also submits blank responses for every editable field and '
  'compares the saved file to verify that its bytes remain unchanged.')
p('If a value is invalid, the entire edit is rejected and the program returns to '
  'the menu. It does not apply the earlier fields from the same operation. The user '
  'can select the record again and retry.')
new()

p('Validation and error handling', 'H2')
table(['Field or condition', 'Rule in this implementation'], [
    ('Group code / year', '1-20 ASCII letters, digits, hyphens or underscores; unique and case-sensitive. Year 1900-2100.'),
    ('Student name', '1-120 bytes, at least one non-space character, no control characters.'),
    ('Birth date', 'YYYY-MM-DD, real calendar date from 1900-01-01 through the current local date; leap-year checks.'),
    ('Average score', 'Finite numeric value from 0 to 100 inclusive.'),
    ('Phone', '7-15 digits within 32 bytes; optional initial +, spaces, hyphens and parentheses. No claim of telephone-number verification.'),
    ('Selections', 'Existing group and student ID. Complete numeric responses without trailing characters.'),
    ('Capacity', 'At most 1,000 groups, 10,000 students per group and 100,000 students total.'),
], [118, 350])
terminal('Error: Average score must be a finite number from 0 to 100.\n'
         'No change was saved.',
         'Figure 4.6 - Output captured when an edit supplies score 101.')
assert 'Error: Average score must be a finite number from 0 to 100.\nNo change was saved.' in \
    RESULTS['console_sessions']['Invalid student score']['stdout']
p('All console text is read as a complete line. The console trims surrounding '
  'spaces. UTF-8 names can be stored, although their display depends on the terminal. '
  'Name and phone length limits count bytes. Invalid input returns to the main menu '
  'instead of attempting a partial field-by-field correction.')
new()

p('File format and recovery', 'H2')
p('The file is versioned plain text. A header identifies the format. NEXT_ID stores '
  'the next unused student ID, and GROUPS gives the number of group records. Each '
  'GROUP declares its student count. Each STUDENT line contains all of its fields.')
terminal((ROOT / 'examples' / 'sample_data.txt').read_text(encoding='utf-8'))
p('Text fields are quoted, with embedded quotes and backslashes escaped by '
  'std::quoted [5]. Scores are saved with max_digits10 precision and shown to two '
  'decimal places in the interface. The display rounding does not alter stored values.')
p('Before replacing the data file, the program writes and closes a sibling .tmp '
  'file. If an old main file exists, it is renamed to .bak. The completed .tmp is '
  'then renamed to the main filename. Only after that step does the program update '
  'its in-memory records. The temporary backup is removed after a successful replacement. '
  'Standard filesystem operations provide these steps on Windows and POSIX [6].')
p('A detected .bak or .tmp prevents startup and further saves. To recover, close '
  'all instances and first copy the main, backup and temporary files to a safe place. '
  'Inspect the copies. The .bak normally holds the previous version, while a complete '
  '.tmp may hold a pending version. Restore one valid copy to the main filename and '
  'move the recovery files aside before restarting.')
p('The replacement sequence is intended for ordinary single-process failures. '
  'Restoring the original is attempted if replacement fails. It is not a fully '
  'transactional, power-loss-safe database. There is no locking or encryption, '
  'and two instances must not write the same data file. Important records need '
  'separate backups.')
new()

h('4.5 Testing and results', 2)
p('Verification was performed on 21 November 2026 using the Zig 0.17.1 C++ compiler '
  'driver. The application and C++ test executable were compiled for Windows x86-64 '
  'and Linux x86-64 with -std=c++17 -Wall -Wextra -Wpedantic -Werror -O2. All four '
  'builds completed successfully without compiler warnings. Native Windows execution '
  'and local Linux execution in WSL were both tested.')
table(['Suite', 'Windows', 'Linux'], [
    ('Direct C++ database checks', '132 passed', '132 passed'),
    ('End-to-end console cases', '36 passed', '36 passed'),
    ('Application build', 'Passed', 'Passed'),
    ('Test executable build', 'Passed', 'Passed'),
], [258, 105, 105])
p('The C++ tests call the real database operations and use real files in isolated '
  'temporary directories. Each assertion checks a specific result. They cover '
  'valid and invalid fields, leap years, score boundaries, duplicate group codes, '
  'duplicate student names, every editable field, transfers and group renaming.')
p('Persistence checks reload the file and compare IDs, escaped text and exact '
  'double values. They verify that deleting records does not reuse IDs after a '
  'restart. Recovery files, missing output directories, malformed records, bad '
  'versions, duplicate IDs and unexpected trailing data are also tested. Failed '
  'loads preserve the prior in-memory collection and the input file.')
p('The Python suite launches the compiled program with scripted console input. '
  'It checks expected output and exit codes, then compares saved bytes after '
  'rejected edits, cancelled deletions and interrupted prompts. The 36 case names '
  'and results are listed in Appendix C. The machine-readable records, captured '
  'sessions and source hashes are included alongside the report.')
p('These results establish the tested behaviour of this version. They do not '
  'simulate sudden power loss or concurrent processes. CMake and Microsoft cl '
  'commands are supplied as alternative build instructions; the recorded compilation '
  'used Zig, not those alternative tools.')
new()

p('Observed results and reproducibility', 'H2')
terminal('Windows:\nPASS: 132 database checks.\nPASS: 36 end-to-end console cases.\n\n'
         'Linux (local WSL):\nPASS: 132 database checks.\nPASS: 36 end-to-end console cases.',
         'Figure 4.7 - Summary printed by the completed test suites.')
terminal(excerpt('Restart restores records', 'Group: CE-101 | Students: 2', '\n1. Add group'),
         'Figure 4.8 - Records displayed by a new process after loading the saved file.')
p('The editing case renamed CE-101 to CE-201, changed its year, then moved student '
  'ID 1 to CE-102 while changing the name, date, score and phone. The output in '
  'Figure 4.5 shows the edited record in its destination group. The tests also '
  'verify that an invalid transfer does not remove the source record.')
p('The source folder contains direct compiler commands in README.md. After building '
  'the application, run studbook_tests for direct checks and python '
  'tests/cli_tests.py --exe followed by the executable path for the console suite. '
  'The tests use fictional records and isolated files. A sample dataset is supplied '
  'for a separate manual demonstration.')
p('The console figures are excerpts of actual program output from the automated '
  'Windows run, typeset for readability. They are not operating-system screenshots. '
  'Input is listed separately where needed, because piped test input is not echoed '
  'by the program.')
new()

h('Conclusions')
p('The completed application implements the selected School Students Database '
  'topic. Groups and students can be created, displayed, edited and deleted. '
  'Editing includes renaming a group, changing every student field and moving '
  'a student to another existing group while preserving the student ID.')
p('The nested vector model keeps ownership simple. Counts are calculated from '
  'the stored collections, and IDs distinguish students with identical names. '
  'A versioned text format preserves records and the ID counter between sessions. '
  'Validation occurs both during modification and while loading a file.')
p('The application separates console interaction from data operations. Changes '
  'are prepared on a candidate copy, checked and saved before becoming current. '
  'Deletion prompts reduce accidental removal, and interrupted input does not '
  'accept an incomplete record. Corrupt data and recovery files are reported '
  'rather than silently discarded.')
p('The recorded verification passed on Windows and Linux: 132 direct database '
  'checks and 36 console cases on each platform, with clean C++17 builds. The '
  'tests exercise normal workflows and failure cases, including editing and '
  'persistence after restarting.')
p('The main limitations are the single-process text-file design, full-file '
  'rewrites and absence of access controls. Future development could add search '
  'and sorting, a graphical interface, automatic backup management, and a '
  'transactional database for larger collections. These are possible extensions '
  'and are not represented as completed features.')
new()

h('References')
refs = [
    ('UzhNU Moodle. Programming, part 2. Explanatory note assignment and Explanatory note example.pdf. '
     'The supplied example was used for the report structure and general task model.',
     'https://moodle.uzhnu.edu.ua/mod/assign/view.php?id=73678'),
    ('UzhNU Moodle. Programming, part 2. Project assignment.',
     'https://moodle.uzhnu.edu.ua/mod/assign/view.php?id=73679'),
    ('Microsoft Learn. C++ Standard Library: vector class.',
     'https://learn.microsoft.com/en-us/cpp/standard-library/vector-class'),
    ('Microsoft Learn. C++ Standard Library: &lt;fstream&gt;.',
     'https://learn.microsoft.com/en-us/cpp/standard-library/fstream'),
    ('Microsoft Learn. C++ Standard Library: &lt;iomanip&gt; functions, including quoted.',
     'https://learn.microsoft.com/en-us/cpp/standard-library/iomanip-functions'),
    ('Microsoft Learn. C++ Standard Library: &lt;filesystem&gt;.',
     'https://learn.microsoft.com/en-us/cpp/standard-library/filesystem'),
]
for i, (description, url) in enumerate(refs, 1):
    p(f'[{i}] {description}<br/><link href="{escape(url)}" color="#165587">{escape(url)}</link><br/>'
      'Accessed 21 November 2026.', 'SmallText')
p('The project Classroom invitation currently redirects to GitHub\'s retirement '
  'announcement. The report and source files are prepared locally for review '
  'before uploading. No repository URL or submission status is claimed here.')
new()

h('Appendix A. Editing and commit flowchart')
story.append(Diagram('edit'))
p('Figure A.1 - A modification is published only after validation and successful saving.', 'Caption')
p('End-of-input before all prompts are complete returns from the console without '
  'calling commit. A missing group, invalid value or failed save follows the error '
  'path. A successful student transfer changes the two group collections together '
  'in the candidate and preserves the student ID.')
new()

h('Appendix B. Application source code')
p('This listing contains all five application source/header files. Line numbers '
  'are added for reference; the files in src/ contain compilable source without '
  'those printed prefixes. Long lines may wrap in this listing.', 'SmallText')
for index, name in enumerate(['database.hpp', 'database.cpp', 'console.hpp', 'console.cpp', 'main.cpp']):
    if index:
        story.append(Spacer(1, 12))
    p(name, 'FileHeading')
    lines = []
    for number, line in enumerate((ROOT / 'src' / name).read_text(encoding='utf-8').splitlines(), 1):
        chunks = textwrap.wrap(line, width=104, expand_tabs=False, replace_whitespace=False,
                               drop_whitespace=False) or ['']
        lines.append(f'{number:3}  ' + chunks[0])
        lines.extend('     ' + chunk for chunk in chunks[1:])
    story.append(Preformatted('\n'.join(lines), styles['Listing']))
new()

h('Appendix C. Console test register')
p('Each case passed on both Windows and Linux. These are 36 end-to-end cases, '
  'in addition to the 132 direct database checks on each platform.', 'SmallText')
table(['No.', 'Console case', 'Result'],
      [(str(i), row['name'], 'Pass / Pass') for i, row in enumerate(RESULTS['results'], 1)],
      [32, 350, 86])

if __name__ == '__main__':
    destination = DOCS / 'Explanatory_Note.pdf'
    document = Report(str(destination), pagesize=A4, leftMargin=25 * mm,
                      rightMargin=20 * mm, topMargin=22 * mm, bottomMargin=20 * mm,
                      title='School Students Database - Explanatory Note',
                      author='Кортні Шілдс Скаллі')
    frame = Frame(document.leftMargin, document.bottomMargin,
                  document.width, document.height, id='body', leftPadding=0,
                  rightPadding=0, topPadding=0, bottomPadding=0)
    document.addPageTemplates(PageTemplate(id='report', frames=frame, onPage=decorate))
    document.multiBuild(story)
    print(f'Created {destination}')
