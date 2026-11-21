"""End-to-end console tests. Uses Python's standard library only."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--exe', type=Path, default=ROOT / 'build' / 'studbook')
parser.add_argument('--wsl', help='Optional local WSL distribution for running a Linux build')
parser.add_argument('--results', type=Path, help='Write the results and selected console sessions as JSON')
options = parser.parse_args()
results = []
sessions = {}


def runtime_path(path):
    path = Path(path).resolve()
    if options.wsl:
        return '/mnt/host/' + path.drive[0].lower() + path.as_posix()[2:]
    return str(path)


def run(name, directory, commands='', *, data='students.txt', code=0,
        contains=(), error_contains=(), extra_args=None, capture=False):
    args = extra_args if extra_args is not None else [runtime_path(directory / data)]
    command = [runtime_path(options.exe), *args]
    if options.wsl:
        command = ['wsl', '-d', options.wsl, '--exec', *command]
    process = subprocess.run(command, input=commands, encoding='utf-8',
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             cwd=ROOT if options.wsl else directory, timeout=20)
    assert process.returncode == code, (name, process.returncode, process.stdout, process.stderr)
    for text in contains:
        assert text in process.stdout, (name, text, process.stdout)
    for text in error_contains:
        assert text in process.stderr, (name, text, process.stderr)
    if code == 0:
        assert not process.stderr, (name, process.stderr)
    results.append({'name': name, 'exit_code': process.returncode, 'status': 'PASS'})
    if capture:
        sessions[name] = {'input': commands, 'stdout': process.stdout, 'stderr': process.stderr}
    return process.stdout


with tempfile.TemporaryDirectory(prefix='studbook-cli-') as temporary:
    directory = Path(temporary)
    run('First launch and empty displays', directory, '3\n0\n',
        contains=['Loaded 0 group(s) and 0 student(s).', 'No groups yet.', 'Goodbye.'])
    assert not (directory / 'students.txt').exists()
    run('Add groups and students', directory,
        '1\nCE-101\n2026\n1\nCE-102\n2026\n'
        '2\nCE-101\nAlex Morgan\n2008-02-29\n87.5\n+380 50 123 4567\n'
        '2\nCE-101\nSam Taylor\n2007-11-15\n92\n+380 67 234 5678\n3\n4\nCE-101\n0\n',
        contains=['Student added and saved. ID: 1', 'Student added and saved. ID: 2',
                  'Groups: 2 | Students: 2', 'Average score: 87.50'], capture=True)
    run('Restart restores records', directory, '4\nCE-101\n0\n',
        contains=['Loaded 2 group(s) and 2 student(s).', 'Alex Morgan', 'Sam Taylor'], capture=True)
    run('Rename group and change year', directory, '5\nCE-101\nCE-201\n2027\n3\n0\n',
        contains=['Group updated and saved.', 'Group: CE-201 | Year: 2027 | Students: 2'])
    run('Edit every student field and move group', directory,
        '6\nCE-201\n1\nCE-102\nAlex Morgan-Reed\n2008-03-01\n95.25\n+380 50 111 2233\n'
        '4\nCE-102\n3\n0\n',
        contains=['Student updated and saved. ID: 1', 'Name: Alex Morgan-Reed',
                  'Birth date: 2008-03-01 | Average score: 95.25', 'Phone: +380 50 111 2233',
                  'Group: CE-201 | Year: 2027 | Students: 1'], capture=True)
    before = (directory / 'students.txt').read_bytes()
    run('Blank edit fields keep current values', directory, '6\nCE-102\n1\n\n\n\n\n\n0\n',
        contains=['Student updated and saved. ID: 1'])
    assert (directory / 'students.txt').read_bytes() == before
    invalid = [
        ('Non-numeric menu', 'hello\n0\n', 'valid number'),
        ('Menu with trailing characters', '3x\n0\n', 'extra characters'),
        ('Out-of-range menu', '9\n0\n', 'option from 0 to 8'),
        ('Non-integer menu', '2.5\n0\n', 'extra characters'),
        ('Duplicate group', '1\nCE-102\n2026\n0\n', 'already exists'),
        ('Invalid group year', '1\nB\n1899\n0\n', 'between 1900 and 2100'),
        ('Invalid group code', '1\nbad code\n2026\n0\n', 'letters, digits'),
        ('Missing group', '4\nmissing\n0\n', 'Group not found'),
        ('Missing student ID', '8\nCE-102\n999\n0\n', 'Student ID not found'),
        ('Invalid group rename', '5\nCE-102\nCE-201\n2026\n0\n', 'already exists'),
        ('Invalid student score', '6\nCE-102\n1\n\n\n\n101\n\n0\n', 'finite number'),
        ('Student move to missing group', '6\nCE-102\n1\nmissing\n\n\n\n\n0\n', 'Group not found'),
    ]
    for name, commands, message in invalid:
        run(name, directory, commands, contains=['Error:', message, 'Goodbye.'], capture=name == 'Invalid student score')
        assert (directory / 'students.txt').read_bytes() == before, name
    run('Cancelled student deletion', directory, '8\nCE-102\n1\nno\n0\n',
        contains=['Deletion cancelled.'])
    run('Cancelled group deletion', directory, '7\nCE-102\nno\n0\n',
        contains=['1 student(s).', 'Deletion cancelled.'])
    assert (directory / 'students.txt').read_bytes() == before
    for name, commands in [('EOF at menu', ''), ('EOF during student entry', '2\nCE-102\nIncomplete\n'),
                           ('EOF during student edit', '6\nCE-102\n1\n\nChanged\n'),
                           ('EOF at delete confirmation', '7\nCE-102\n')]:
        run(name, directory, commands, contains=['Input closed. No incomplete changes were saved.'])
        assert (directory / 'students.txt').read_bytes() == before, name
    run('Confirmed student deletion', directory, '8\nCE-201\n2\nYES\n4\nCE-201\n0\n',
        contains=['Student deleted and saved.', 'No students in this group.'])
    run('Confirmed group deletion removes its students', directory, '7\nCE-102\nYES\n3\n0\n',
        contains=['Group deleted and saved.', 'Groups: 1 | Students: 0'])
    run('Deletions survive restart', directory, '3\n0\n',
        contains=['Loaded 1 group(s) and 0 student(s).'])
    run('Zero score boundary', directory, '2\nCE-201\nBoundary Zero\n2000-01-01\n0\n1234567\n0\n',
        contains=['Student added and saved. ID: 3'])
    run('Hundred score boundary', directory,
        '2\nCE-201\nBoundary Hundred\n2000-01-01\n100\n1234567\n4\nCE-201\n0\n',
        contains=['Average score: 0.00', 'Average score: 100.00'])
    run('Help argument', directory, extra_args=['--help'], contains=['Usage: studbook'])
    run('Extra arguments rejected', directory, extra_args=['one', 'two'], code=1,
        contains=['Usage: studbook'])
    sample = ROOT / 'examples' / 'sample_data.txt'
    run('Provided sample data loads', directory, '3\n4\nCE-101\n0\n',
        extra_args=[runtime_path(sample)],
        contains=['Loaded 2 group(s) and 3 student(s).', 'Sam Taylor'])
    malformed = directory / 'malformed.txt'
    malformed.write_text('STUDBOOK 99\n', encoding='utf-8')
    run('Malformed file refuses startup', directory, data=malformed.name, code=1,
        error_contains=['Unsupported data format', 'has not been changed.'])
    assert malformed.read_text() == 'STUDBOOK 99\n'
    run('Directory refuses startup', directory, extra_args=[runtime_path(directory)], code=1,
        error_contains=['not a regular file'])
    run('Save failure recovers to menu', directory, '1\nA\n2026\n3\n0\n',
        data='nonexistent/data.txt',
        contains=['Error:', 'No change was saved.', 'Groups: 0 | Students: 0', 'Goodbye.'])
    recovery = directory / 'students.txt.bak'
    recovery.write_text('recovery copy', encoding='utf-8')
    run('Recovery file prevents unsafe startup', directory, code=1,
        error_contains=['Recovery file detected'])

summary = {
    'date': '2026-11-21',
    'cli_cases_passed': len(results),
    'results': results,
    'console_sessions': sessions,
    'source_sha256': {str(p.relative_to(ROOT)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in sorted((ROOT / 'src').glob('*'))},
}
if options.results:
    options.results.write_text(json.dumps(summary, indent=2), encoding='utf-8')
print(f'PASS: {len(results)} end-to-end console cases.')
