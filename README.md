# Studbook - School Students Database

Course project for UzhNU Programming, part 2. Studbook is a C++17 console program
for keeping student records in groups. It can add, display, edit and delete both
groups and students, and saves each completed change to a text file.

## Build and run

The program uses the C++ standard library only. A C++17 compiler is needed to
build it. No database server, third-party C++ libraries or package manager is
required. Run these commands from this project folder.

With GCC or Clang:

```sh
g++ -std=c++17 -Wall -Wextra -Wpedantic -O2 src/main.cpp src/database.cpp src/console.cpp -o studbook
./studbook
```

On Windows, choose `-o studbook.exe` and run `.\studbook.exe` in PowerShell.
With Microsoft C++ Build Tools, open a Developer Command Prompt and use:

```bat
cl /std:c++17 /EHsc /W4 /utf-8 src\main.cpp src\database.cpp src\console.cpp /Fe:studbook.exe
studbook.exe
```

CMake is an optional alternative:

```sh
cmake -S . -B build
cmake --build build --config Release
ctest --test-dir build -C Release --output-on-failure
```

The default file is `students_data.txt` in the current working directory. A
different filename can be supplied as the only argument:

```sh
./studbook "my students.txt"
```

To try the fictional sample records, copy `examples/sample_data.txt` to a new
working file and supply that file's path. Changes affect whichever file you open.
`--help` displays the command syntax. Exit is menu option `0`.

## Using the program

| Option | Action |
| --- | --- |
| 1 | Add a group with a unique code and a year. |
| 2 | Add a student to an existing group. A student ID is assigned automatically. |
| 3 | Show all groups, their years, and student counts. |
| 4 | Show the students and all their details in a selected group. |
| 5 | Edit a group's code and year. Its students remain attached. |
| 6 | Edit a student's name, birth date, score and phone, or move the student to another existing group. The ID stays the same. |
| 7 | Delete a group and all of its students after confirmation. |
| 8 | Delete a selected student after confirmation. |
| 0 | Exit. Completed changes have already been saved. |

Enter one response per line. Names do not need quotes at the console. In an edit,
leave a field blank to keep its current value. Select students by ID, so students
with the same name can be distinguished. Deletions require the exact word `YES`.
Any other response cancels the deletion.

If an entry is invalid, the whole operation is cancelled with an error message
and the menu appears again. Previously saved records are kept. Closing standard
input during an operation also cancels that incomplete operation.

## Validation rules

These limits are implementation choices for this project.

- Group codes are case-sensitive and contain 1-20 ASCII letters, digits,
  hyphens or underscores. Group years are 1900-2100.
- Names contain 1-120 bytes, include a non-space character, and contain no control
  characters. UTF-8 names can be stored; display depends on the terminal encoding.
- Birth dates use `YYYY-MM-DD`, must be real dates, and fall between 1900-01-01
  and the computer's current local date. Leap years are checked.
- Average scores must be finite numbers between 0 and 100, inclusive.
- Phones contain 7-15 digits and at most 32 bytes. An initial `+`, spaces,
  hyphens and parentheses are allowed. This checks the format, not whether a
  number actually exists.
- The database supports up to 1,000 groups, 10,000 students per group and 100,000
  students in total. Student IDs are positive integers and are not reused after
  deletion, including across restarts.

## File storage and recovery

The text format starts with `STUDBOOK 1`, followed by `NEXT_ID` and `GROUPS`
records. Each group stores its student count. Each student stores an ID, name,
birth date, full-precision score and phone. Quoted text escapes embedded quotes
and backslashes. `examples/sample_data.txt` shows a complete file.

Loading validates the entire file before replacing the in-memory data. Invalid
versions, duplicate codes or IDs, invalid fields, missing records and extra data
are rejected. A missing file means a new empty database; an existing empty or
malformed file is an error and is left untouched.

A change is made on a copy, validated, and written to `<filename>.tmp`. If a
previous data file exists, it is renamed to `<filename>.bak` before the completed
temporary file takes its place. Memory is updated only after that replacement
succeeds. The temporary backup is then removed. Ordinary write/rename failures
are reported and restoration of the original is attempted.

If a `.bak` or `.tmp` file remains after an interruption, startup and further
saves stop rather than discard it. Close all instances, copy all available files
somewhere safe, then inspect them. A `.bak` normally contains the previous
version; a complete `.tmp` may contain the pending version. Choose a valid copy
as the main filename and move the recovery files out of the way before restarting.
Keep a separate backup of important data.

This is a local, single-user teaching project. Open one instance per data file.
There is no file locking, encryption, authentication or guarantee against power
loss. File replacement is staged rather than a transactional database system.
The local computer's date and permissions affect validation and saving.

## Tests

Build and run the C++ database tests:

```sh
g++ -std=c++17 -Wall -Wextra -Wpedantic -O2 -Isrc tests/database_tests.cpp src/database.cpp src/console.cpp -o studbook_tests
./studbook_tests
```

For end-to-end console tests, Python 3 is optional:

```sh
python tests/cli_tests.py --exe ./studbook
```

On Windows, supply the executable's actual path, for example
`python tests/cli_tests.py --exe .\studbook.exe`.
Tests use isolated temporary files. They cover editing, group transfers,
duplicate names, validation boundaries, restart persistence, exact numeric and
escaped-text round trips, failed saves, recovery files, malformed input files,
confirmation prompts and interrupted console input. See `docs/Verification.txt`
and `docs/test_results.json` for the recorded results.

## Files

- `src/` - the complete C++ program, split into data storage and console modules.
- `tests/` - C++ database checks and Python console tests.
- `examples/sample_data.txt` - fictional demonstration records.
- `docs/Explanatory_Note.pdf` - the explanatory note for Moodle.
- `docs/build_report.py` - editable report text and PDF generator. Regenerating
  the report requires Python 3 and ReportLab, but running Studbook does not.
- `build/` - locally compiled binaries, excluded from Git.

## Coursework

Project: https://moodle.uzhnu.edu.ua/mod/assign/view.php?id=73679

Explanatory note: https://moodle.uzhnu.edu.ua/mod/assign/view.php?id=73678

The topic is School Students Database. The supplied explanatory note example was
used as a guide to the report structure. This implementation includes editing
records as well as adding, displaying, deleting, saving and loading them.
