#include "console.hpp"
#include <chrono>
#include <cmath>
#include <fstream>
#include <functional>
#include <iostream>
#include <iterator>
#include <limits>
#include <sstream>
#include <stdexcept>

using studbook::Database;
using studbook::Student;
namespace fs = std::filesystem;
int checks = 0;

void check(bool condition, const std::string& message) {
    if (!condition) throw std::runtime_error("FAILED: " + message);
    ++checks;
}

void rejects(const std::function<void()>& action, const std::string& text) {
    try { action(); }
    catch (const std::exception& error) {
        check(std::string(error.what()).find(text) != std::string::npos,
              "Expected error containing: " + text + "; got: " + error.what());
        return;
    }
    throw std::runtime_error("FAILED: expected rejection: " + text);
}

std::string contents(const fs::path& path) {
    std::ifstream input(path, std::ios::binary);
    return {std::istreambuf_iterator<char>(input), std::istreambuf_iterator<char>()};
}

void write(const fs::path& path, const std::string& text) {
    std::ofstream output(path, std::ios::binary);
    output << text;
    if (!output) throw std::runtime_error("Could not write test fixture.");
}

Student sample() { return {0, "Alex Morgan", "2008-02-29", 87.5, "+380 50 123 4567"}; }

void testValidation() {
    for (auto year : {1900, 2026, 2100}) {
        studbook::validateGroup("CE-101_a", year);
        check(true, "Valid group boundary");
    }
    for (const auto& code : {"", "A B", "bad/code", "ABCDEFGHIJKLMNOPQRSTU"})
        rejects([&] { studbook::validateGroup(code, 2026); }, "");
    for (auto year : {1899, 2101})
        rejects([&] { studbook::validateGroup("A", year); }, "year");
    for (const auto& date : {"1900-01-01", "2000-02-29", "2008-02-29"}) {
        auto s = sample(); s.birthDate = date;
        studbook::validateStudent(s); check(true, "Valid dates");
    }
    for (const auto& date : {"1900-02-29", "2001-02-29", "2008-04-31", "2008-13-01",
                             "2008-00-01", "2008-01-00", "1899-12-31", "9999-01-01",
                             "2008-2-29", "2008/02/29", "abcd-ef-gh"}) {
        auto s = sample(); s.birthDate = date;
        rejects([&] { studbook::validateStudent(s); }, "birth date");
    }
    for (double score : {0.0, 100.0, 0.125, 99.999}) {
        auto s = sample(); s.averageScore = score;
        studbook::validateStudent(s); check(true, "Valid scores");
    }
    for (double score : {-0.01, 100.01, std::numeric_limits<double>::infinity(),
                         std::numeric_limits<double>::quiet_NaN()}) {
        auto s = sample(); s.averageScore = score;
        rejects([&] { studbook::validateStudent(s); }, "finite number");
    }
    for (const auto& name : {std::string(), std::string("   "), std::string("A\nB"),
                             std::string(121, 'A')}) {
        auto s = sample(); s.name = name;
        rejects([&] { studbook::validateStudent(s); }, "Name");
    }
    for (const auto& phone : {"1234567", "+123456789012345", "+380 (50) 123-4567"}) {
        auto s = sample(); s.phone = phone;
        studbook::validateStudent(s); check(true, "Valid phone");
    }
    for (const auto& phone : {"", "123456", "1234567890123456", "12+3456789", "12345abcde"}) {
        auto s = sample(); s.phone = phone;
        rejects([&] { studbook::validateStudent(s); }, "Phone");
    }
}

void testOperations(const fs::path& root) {
    auto path = root / "round trip.txt";
    Database db(path);
    db.load();
    check(db.groups().empty() && !fs::exists(path), "First launch does not create a file");
    db.addGroup("CE-101", 2026);
    db.addGroup("CE-102", 2025);
    check(db.groups().size() == 2, "Add groups");
    auto before = contents(path);
    rejects([&] { db.addGroup("CE-101", 2026); }, "already exists");
    check(contents(path) == before && db.groups().size() == 2, "Duplicate group rollback");
    int first = db.addStudent("CE-101", sample());
    int second = db.addStudent("CE-101", sample());
    check(first != second && db.studentCount() == 2, "Duplicate names have distinct IDs");
    auto s = db.student("CE-101", first);
    s.name = "O\"Brien \\ Test";
    s.birthDate = "2000-02-29";
    s.averageScore = 100.0 / 3.0;
    s.phone = "+123456789012345";
    db.editStudent("CE-101", first, "CE-101", s);
    check(db.student("CE-101", first).name == s.name, "Edit name");
    check(db.student("CE-101", first).birthDate == s.birthDate, "Edit date");
    check(db.student("CE-101", first).averageScore == s.averageScore, "Edit score");
    check(db.student("CE-101", first).phone == s.phone, "Edit phone");
    db.editStudent("CE-101", first, "CE-102", s);
    check(db.group("CE-101").students.size() == 1 &&
          db.student("CE-102", first).id == first, "Move preserves ID");
    db.editGroup("CE-102", "CE-202", 2027);
    check(db.group("CE-202").year == 2027 && db.student("CE-202", first).id == first,
          "Group rename keeps student association");
    before = contents(path);
    rejects([&] { db.editGroup("CE-202", "CE-101", 2027); }, "already exists");
    rejects([&] { db.editStudent("CE-202", first, "missing", s); }, "not found");
    auto invalid = s; invalid.averageScore = -1;
    rejects([&] { db.editStudent("CE-202", first, "CE-101", invalid); }, "finite number");
    rejects([&] { db.deleteStudent("CE-202", 999); }, "not found");
    rejects([&] { db.deleteGroup("missing"); }, "not found");
    check(contents(path) == before && db.studentCount() == 2, "Failed edits leave file unchanged");
    Database restored(path);
    restored.load();
    check(restored.groups().size() == 2 && restored.studentCount() == 2, "Restart counts");
    check(restored.student("CE-202", first).name == s.name, "Quotes and slashes round trip");
    check(restored.student("CE-202", first).averageScore == s.averageScore, "Exact score round trip");
    restored.deleteStudent("CE-101", second);
    check(restored.group("CE-101").students.empty(), "Delete one of duplicate names by ID");
    restored.deleteGroup("CE-202");
    check(restored.studentCount() == 0, "Delete nonempty group cascades");
    restored.load();
    int next = restored.addStudent("CE-101", sample());
    check(next > second, "Deleted IDs are not reused after restart");
    restored.deleteGroup("CE-101");
    restored.load();
    check(restored.groups().empty(), "Empty database round trip");
    check(!fs::exists(path.string() + ".tmp") && !fs::exists(path.string() + ".bak"),
          "Successful save cleans temporary files");

    Database unwritable(root / "missing" / "data.txt");
    unwritable.load();
    rejects([&] { unwritable.addGroup("A", 2026); }, "temporary");
    check(unwritable.groups().empty(), "Failed save leaves memory unchanged");
    auto blocked = root / "blocked.txt";
    Database protectedDb(blocked); protectedDb.load(); protectedDb.addGroup("A", 2026);
    before = contents(blocked);
    for (const auto& suffix : {".tmp", ".bak"}) {
        auto recovery = fs::path(blocked.string() + suffix);
        write(recovery, "keep this recovery file");
        rejects([&] { protectedDb.addGroup("B", 2026); }, "recovery file");
        check(contents(blocked) == before && contents(recovery) == "keep this recovery file",
              "Recovery files and original protected");
        rejects([&] { protectedDb.load(); }, "Recovery file");
        fs::remove(recovery);
    }
    Database directory(root);
    rejects([&] { directory.load(); }, "regular file");
}

void testMalformed(const fs::path& root) {
    const std::string prefix = "STUDBOOK 1\nNEXT_ID 3\nGROUPS 1\nGROUP \"A\" 2026 1\n";
    const std::string student = "STUDENT 1 \"Alex\" \"2008-02-29\" 50 \"1234567\"\n";
    const std::vector<std::string> bad = {
        "", "STUDBOOK 2\n", "STUDBOOK 1\n", "STUDBOOK 1\nNEXT_ID 0\nGROUPS 0\n",
        "STUDBOOK 1\nNEXT_ID 1 extra\nGROUPS 0\n",
        "STUDBOOK 1\nNEXT_ID 1\nGROUPS -1\n",
        "STUDBOOK 1\nNEXT_ID 1\nGROUPS 1001\n",
        "STUDBOOK 1\nNEXT_ID 1\nGROUPS 1\nGROUP \"A\" 2026 10001\n",
        prefix, prefix + student + "trailing\n",
        prefix + "STUDENT 0 \"Alex\" \"2008-02-29\" 50 \"1234567\"\n",
        prefix + "STUDENT 3 \"Alex\" \"2008-02-29\" 50 \"1234567\"\n",
        prefix + "STUDENT 1 \"Alex\" \"2007-02-29\" 50 \"1234567\"\n",
        prefix + "STUDENT 1 \"Alex\" \"2008-02-29\" 101 \"1234567\"\n",
        prefix + "STUDENT 1 \"Alex\" \"2008-02-29\" nan \"1234567\"\n",
        prefix + student.substr(0, student.size() - 1) + " extra\n",
        "STUDBOOK 1\nNEXT_ID 3\nGROUPS 2\nGROUP \"A\" 2026 0\nGROUP \"A\" 2026 0\n",
        "STUDBOOK 1\nNEXT_ID 3\nGROUPS 1\nGROUP \"A\" 2026 2\n" + student + student
    };
    auto path = root / "malformed.txt";
    Database db(path); db.load(); db.addGroup("Original", 2026);
    for (const auto& text : bad) {
        write(path, text);
        bool rejected = false;
        try { db.load(); } catch (const std::exception&) { rejected = true; }
        check(rejected, "Malformed file rejected");
        check(db.groups().size() == 1 && db.group("Original").year == 2026,
              "Failed load keeps existing in-memory state");
        check(contents(path) == text, "Failed load never overwrites source file");
    }
    write(path, "STUDBOOK 1\r\nNEXT_ID 3\r\nGROUPS 1\r\nGROUP \"A\" 2026 1\r\n"
          "STUDENT 1 \"Alex\" \"2008-02-29\" 50 \"1234567\"\r\n");
    db.load(); check(db.student("A", 1).averageScore == 50, "CRLF input accepted");
}

int main() {
    const auto stamp = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    const auto root = fs::temp_directory_path() / ("studbook-test-" + std::to_string(stamp));
    try {
        fs::create_directory(root);
        testValidation();
        testOperations(root);
        testMalformed(root);
        fs::remove_all(root);
        std::cout << "PASS: " << checks << " database checks.\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << error.what() << "\nFixtures retained at " << root << '\n';
        return 1;
    }
}
