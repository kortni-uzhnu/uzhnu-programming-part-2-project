#include "console.hpp"
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>

namespace studbook {
namespace {
struct InputClosed {};

std::string readLine(std::istream& input, std::ostream& output, const std::string& prompt) {
    output << prompt << std::flush;
    std::string text;
    if (!std::getline(input, text)) throw InputClosed{};
    auto start = text.find_first_not_of(" \t\r");
    if (start == std::string::npos) return "";
    return text.substr(start, text.find_last_not_of(" \t\r") - start + 1);
}

template<class T>
T parseNumber(const std::string& text) {
    std::istringstream stream(text);
    T value{};
    if (!(stream >> value)) throw std::runtime_error("Enter a valid number.");
    stream >> std::ws;
    if (!stream.eof()) throw std::runtime_error("Enter a number without extra characters.");
    return value;
}

template<class T>
T readNumber(std::istream& in, std::ostream& out, const std::string& prompt) {
    return parseNumber<T>(readLine(in, out, prompt));
}

std::string editText(std::istream& in, std::ostream& out,
                     const std::string& label, const std::string& current) {
    auto value = readLine(in, out, label + " [" + current + "]: ");
    return value.empty() ? current : value;
}

template<class T>
T editNumber(std::istream& in, std::ostream& out, const std::string& label, T current) {
    std::ostringstream prompt;
    prompt << label << " [" << current << "]: ";
    auto text = readLine(in, out, prompt.str());
    return text.empty() ? current : parseNumber<T>(text);
}

void displayGroups(const Database& db, std::ostream& out) {
    out << "\nGroups: " << db.groups().size() << " | Students: " << db.studentCount() << '\n';
    if (db.groups().empty()) out << "No groups yet.\n";
    for (const auto& group : db.groups())
        out << "Group: " << group.code << " | Year: " << group.year
            << " | Students: " << group.students.size() << '\n';
}

void displayStudents(const Group& group, std::ostream& out) {
    out << "\nGroup: " << group.code << " | Students: " << group.students.size() << '\n';
    if (group.students.empty()) out << "No students in this group.\n";
    for (const auto& student : group.students) {
        std::ostringstream score;
        score << std::fixed << std::setprecision(2) << student.averageScore;
        out << "ID: " << student.id << " | Name: " << student.name
            << "\nBirth date: " << student.birthDate << " | Average score: " << score.str()
            << "\nPhone: " << student.phone << '\n';
    }
}

Student readStudent(std::istream& in, std::ostream& out) {
    Student student;
    student.name = readLine(in, out, "Full name: ");
    student.birthDate = readLine(in, out, "Birth date (YYYY-MM-DD): ");
    student.averageScore = readNumber<double>(in, out, "Average score (0-100): ");
    student.phone = readLine(in, out, "Phone: ");
    return student;
}

void perform(int choice, Database& db, std::istream& in, std::ostream& out) {
    if (choice == 3) { displayGroups(db, out); return; }
    auto code = readLine(in, out, "Group code: ");
    if (choice == 1) {
        auto year = readNumber<int>(in, out, "Group year (1900-2100): ");
        db.addGroup(code, year);
        out << "Group added and saved.\n";
    } else if (choice == 2) {
        db.group(code);
        auto record = readStudent(in, out);
        int id = db.addStudent(code, record);
        out << "Student added and saved. ID: " << id << '\n';
    } else if (choice == 4) {
        displayStudents(db.group(code), out);
    } else if (choice == 5) {
        auto group = db.group(code);
        out << "Leave a field blank to keep its current value.\n";
        auto newCode = editText(in, out, "New group code", group.code);
        auto year = editNumber<int>(in, out, "New group year", group.year);
        db.editGroup(code, newCode, year);
        out << "Group updated and saved.\n";
    } else if (choice == 6 || choice == 8) {
        displayStudents(db.group(code), out);
        auto id = readNumber<int>(in, out, "Student ID: ");
        auto record = db.student(code, id);
        if (choice == 6) {
            out << "Leave a field blank to keep its current value.\n";
            auto destination = editText(in, out, "New group code", code);
            record.name = editText(in, out, "Full name", record.name);
            record.birthDate = editText(in, out, "Birth date", record.birthDate);
            record.averageScore = editNumber<double>(in, out, "Average score", record.averageScore);
            record.phone = editText(in, out, "Phone", record.phone);
            db.editStudent(code, id, destination, record);
            out << "Student updated and saved. ID: " << id << '\n';
        } else {
            out << "Delete " << record.name << " (ID " << id << ")?\n";
            if (readLine(in, out, "Type YES to delete: ") == "YES") {
                db.deleteStudent(code, id);
                out << "Student deleted and saved.\n";
            } else out << "Deletion cancelled.\n";
        }
    } else if (choice == 7) {
        const auto& group = db.group(code);
        out << "This will delete group " << code << " and " << group.students.size()
            << " student(s).\n";
        if (readLine(in, out, "Type YES to delete: ") == "YES") {
            db.deleteGroup(code);
            out << "Group deleted and saved.\n";
        } else out << "Deletion cancelled.\n";
    }
}
} // namespace

void runConsole(Database& database, std::istream& input, std::ostream& output) {
    output << "Studbook - School Students Database\n"
           << "Loaded " << database.groups().size() << " group(s) and "
           << database.studentCount() << " student(s).\n";
    try {
        for (;;) {
            output << "\n1. Add group\n2. Add student\n3. Show groups\n4. Show students\n"
                   << "5. Edit group\n6. Edit student / move group\n7. Delete group\n"
                   << "8. Delete student\n0. Exit\n";
            try {
                int choice = readNumber<int>(input, output, "Choice: ");
                if (choice == 0) { output << "Goodbye. All completed changes are saved.\n"; return; }
                if (choice < 1 || choice > 8)
                    throw std::runtime_error("Choose an option from 0 to 8.");
                perform(choice, database, input, output);
            } catch (const std::exception& error) {
                output << "Error: " << error.what() << "\nNo change was saved.\n";
            }
        }
    } catch (const InputClosed&) {
        output << "\nInput closed. No incomplete changes were saved.\n";
    }
}
} // namespace studbook
