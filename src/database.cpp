#include "database.hpp"

#include <algorithm>
#include <cmath>
#include <ctime>
#include <fstream>
#include <iomanip>
#include <limits>
#include <set>
#include <sstream>
#include <stdexcept>
#include <utility>

namespace studbook {
namespace {
constexpr std::size_t maxGroups = 1000;
constexpr std::size_t maxStudentsPerGroup = 10000;
constexpr std::size_t maxStudents = 100000;

std::size_t groupIndex(const std::vector<Group>& groups, const std::string& code) {
    for (std::size_t i = 0; i < groups.size(); ++i)
        if (groups[i].code == code) return i;
    throw std::runtime_error("Group not found: " + code);
}

std::size_t studentIndex(const Group& group, int id) {
    for (std::size_t i = 0; i < group.students.size(); ++i)
        if (group.students[i].id == id) return i;
    throw std::runtime_error("Student ID not found in this group.");
}

bool visibleText(const std::string& text, std::size_t limit) {
    if (text.empty() || text.size() > limit) return false;
    bool nonSpace = false;
    for (unsigned char c : text) {
        if (c < 32 || c == 127) return false;
        if (c != ' ') nonSpace = true;
    }
    return nonSpace;
}

bool validDate(const std::string& date) {
    if (date.size() != 10 || date[4] != '-' || date[7] != '-') return false;
    for (std::size_t i = 0; i < date.size(); ++i)
        if (i != 4 && i != 7 && (date[i] < '0' || date[i] > '9')) return false;
    int y = std::stoi(date.substr(0, 4));
    int m = std::stoi(date.substr(5, 2));
    int d = std::stoi(date.substr(8, 2));
    if (y < 1900 || m < 1 || m > 12) return false;
    const int days[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    int last = days[m - 1];
    if (m == 2 && y % 4 == 0 && (y % 100 != 0 || y % 400 == 0)) ++last;
    if (d < 1 || d > last) return false;
    const auto now = std::time(nullptr);
    const auto* today = std::localtime(&now);
    if (!today) throw std::runtime_error("Cannot read the current date.");
    return y < today->tm_year + 1900 ||
        (y == today->tm_year + 1900 && (m < today->tm_mon + 1 ||
        (m == today->tm_mon + 1 && d <= today->tm_mday)));
}

void checkState(const std::vector<Group>& groups, int nextId) {
    if (groups.size() > maxGroups || nextId < 1)
        throw std::runtime_error("Database limits exceeded.");
    std::set<std::string> codes;
    std::set<int> ids;
    for (const auto& group : groups) {
        validateGroup(group.code, group.year);
        if (!codes.insert(group.code).second)
            throw std::runtime_error("Group code already exists.");
        if (group.students.size() > maxStudentsPerGroup)
            throw std::runtime_error("A group cannot contain more than 10000 students.");
        for (const auto& student : group.students) {
            validateStudent(student);
            if (student.id < 1 || student.id >= nextId || !ids.insert(student.id).second)
                throw std::runtime_error("Invalid or duplicate student ID.");
        }
    }
    if (ids.size() > maxStudents) throw std::runtime_error("Student limit exceeded.");
}

std::istringstream recordLine(std::istream& input) {
    std::string line;
    if (!std::getline(input, line)) throw std::runtime_error("Incomplete data file.");
    return std::istringstream(line);
}

void endOfLine(std::istringstream& line) {
    line >> std::ws;
    if (!line.eof()) throw std::runtime_error("Unexpected data in a record.");
}

void saveFile(const std::filesystem::path& path,
              const std::vector<Group>& groups, int nextId) {
    namespace fs = std::filesystem;
    fs::path temporary = path;
    temporary += ".tmp";
    fs::path backup = path;
    backup += ".bak";
    if (fs::exists(temporary) || fs::exists(backup))
        throw std::runtime_error("A .tmp or .bak recovery file exists. Check it before saving.");
    const bool existed = fs::exists(path);
    if (existed && !fs::is_regular_file(path))
        throw std::runtime_error("The data path is not a regular file.");
    bool movedOriginal = false;
    try {
        std::ofstream output(temporary);
        if (!output) throw std::runtime_error("Cannot open the temporary data file.");
        output << "STUDBOOK 1\nNEXT_ID " << nextId << "\nGROUPS " << groups.size() << '\n';
        output << std::setprecision(std::numeric_limits<double>::max_digits10);
        for (const auto& group : groups) {
            output << "GROUP " << std::quoted(group.code) << ' ' << group.year
                   << ' ' << group.students.size() << '\n';
            for (const auto& student : group.students)
                output << "STUDENT " << student.id << ' ' << std::quoted(student.name)
                       << ' ' << std::quoted(student.birthDate) << ' '
                       << student.averageScore << ' ' << std::quoted(student.phone) << '\n';
        }
        output.close();
        if (!output) throw std::runtime_error("Could not finish writing the data file.");
        if (existed) {
            fs::rename(path, backup);
            movedOriginal = true;
        }
        fs::rename(temporary, path);
    } catch (...) {
        std::error_code ignored;
        if (movedOriginal) fs::rename(backup, path, ignored);
        fs::remove(temporary, ignored);
        throw;
    }
    if (movedOriginal) {
        std::error_code ignored;
        fs::remove(backup, ignored);
    }
}
} // namespace

void validateGroup(const std::string& code, int year) {
    if (code.empty() || code.size() > 20)
        throw std::runtime_error("Group code must contain 1 to 20 characters.");
    for (char c : code)
        if (!((c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z') ||
              (c >= '0' && c <= '9') || c == '-' || c == '_'))
            throw std::runtime_error("Use letters, digits, hyphens or underscores for group codes.");
    if (year < 1900 || year > 2100)
        throw std::runtime_error("Group year must be between 1900 and 2100.");
}

void validateStudent(const Student& student) {
    if (!visibleText(student.name, 120))
        throw std::runtime_error("Name must contain 1 to 120 bytes and no control characters.");
    if (!validDate(student.birthDate))
        throw std::runtime_error("Use a real birth date, YYYY-MM-DD, from 1900 through today.");
    if (!std::isfinite(student.averageScore) || student.averageScore < 0 ||
        student.averageScore > 100)
        throw std::runtime_error("Average score must be a finite number from 0 to 100.");
    if (!visibleText(student.phone, 32))
        throw std::runtime_error("Phone must contain 1 to 32 bytes and no control characters.");
    int digits = 0;
    for (std::size_t i = 0; i < student.phone.size(); ++i) {
        char c = student.phone[i];
        if (c >= '0' && c <= '9') ++digits;
        else if (!(c == ' ' || c == '-' || c == '(' || c == ')' || (c == '+' && i == 0)))
            throw std::runtime_error("Phone accepts digits, an initial +, spaces, hyphens and parentheses.");
    }
    if (digits < 7 || digits > 15)
        throw std::runtime_error("Phone must contain 7 to 15 digits.");
}

Database::Database(std::filesystem::path filename) : filename_(std::move(filename)) {
    if (filename_.empty()) throw std::runtime_error("The data filename cannot be empty.");
}

void Database::load() {
    auto backup = filename_;
    backup += ".bak";
    auto temporary = filename_;
    temporary += ".tmp";
    if (std::filesystem::exists(backup) || std::filesystem::exists(temporary))
        throw std::runtime_error("Recovery file detected (.bak or .tmp). Inspect it before opening the database.");
    if (!std::filesystem::exists(filename_)) { groups_.clear(); nextId_ = 1; return; }
    if (!std::filesystem::is_regular_file(filename_))
        throw std::runtime_error("The data path is not a regular file.");
    std::ifstream input(filename_);
    if (!input) throw std::runtime_error("Cannot open the data file.");
    std::string header;
    if (!std::getline(input, header)) throw std::runtime_error("Empty data file.");
    if (!header.empty() && header.back() == '\r') header.pop_back();
    if (header != "STUDBOOK 1") throw std::runtime_error("Unsupported data format or version.");
    std::string tag;
    int nextId = 0;
    auto line = recordLine(input);
    if (!(line >> tag >> nextId) || tag != "NEXT_ID")
        throw std::runtime_error("Invalid next-ID record.");
    endOfLine(line);
    long long count = 0;
    line = recordLine(input);
    if (!(line >> tag >> count) || tag != "GROUPS" || count < 0 ||
        count > static_cast<long long>(maxGroups)) throw std::runtime_error("Invalid group count.");
    endOfLine(line);
    std::vector<Group> loaded;
    std::size_t total = 0;
    for (long long i = 0; i < count; ++i) {
        Group group;
        long long studentCount = 0;
        line = recordLine(input);
        if (!(line >> tag >> std::quoted(group.code) >> group.year >> studentCount) ||
            tag != "GROUP" || studentCount < 0 ||
            studentCount > static_cast<long long>(maxStudentsPerGroup))
            throw std::runtime_error("Invalid group record.");
        endOfLine(line);
        total += static_cast<std::size_t>(studentCount);
        if (total > maxStudents) throw std::runtime_error("Student limit exceeded.");
        for (long long j = 0; j < studentCount; ++j) {
            Student student;
            line = recordLine(input);
            if (!(line >> tag >> student.id >> std::quoted(student.name)
                >> std::quoted(student.birthDate) >> student.averageScore
                >> std::quoted(student.phone)) || tag != "STUDENT")
                throw std::runtime_error("Invalid student record.");
            endOfLine(line);
            group.students.push_back(std::move(student));
        }
        loaded.push_back(std::move(group));
    }
    input >> std::ws;
    if (!input.eof() || input.bad()) throw std::runtime_error("Unexpected or unreadable trailing data.");
    checkState(loaded, nextId);
    groups_.swap(loaded);
    nextId_ = nextId;
}

const Group& Database::group(const std::string& code) const {
    return groups_[groupIndex(groups_, code)];
}

const Student& Database::student(const std::string& code, int id) const {
    const auto& found = group(code);
    return found.students[studentIndex(found, id)];
}

std::size_t Database::studentCount() const {
    std::size_t total = 0;
    for (const auto& group : groups_) total += group.students.size();
    return total;
}

void Database::commit(std::vector<Group> candidate, int nextId) {
    checkState(candidate, nextId);
    saveFile(filename_, candidate, nextId);
    groups_.swap(candidate);
    nextId_ = nextId;
}

void Database::addGroup(const std::string& code, int year) {
    auto candidate = groups_;
    candidate.push_back({code, year, {}});
    commit(std::move(candidate), nextId_);
}

void Database::editGroup(const std::string& code, const std::string& newCode, int year) {
    auto candidate = groups_;
    auto& found = candidate[groupIndex(candidate, code)];
    found.code = newCode;
    found.year = year;
    commit(std::move(candidate), nextId_);
}

void Database::deleteGroup(const std::string& code) {
    auto candidate = groups_;
    auto index = groupIndex(candidate, code);
    candidate.erase(candidate.begin() + static_cast<std::ptrdiff_t>(index));
    commit(std::move(candidate), nextId_);
}

int Database::addStudent(const std::string& code, Student record) {
    if (nextId_ == std::numeric_limits<int>::max())
        throw std::runtime_error("No more student IDs are available.");
    auto candidate = groups_;
    record.id = nextId_;
    candidate[groupIndex(candidate, code)].students.push_back(std::move(record));
    const int assigned = nextId_;
    commit(std::move(candidate), nextId_ + 1);
    return assigned;
}

void Database::editStudent(const std::string& code, int id,
                           const std::string& destination, Student record) {
    auto candidate = groups_;
    auto from = groupIndex(candidate, code);
    auto to = groupIndex(candidate, destination);
    auto index = studentIndex(candidate[from], id);
    record.id = id;
    if (from == to) candidate[from].students[index] = std::move(record);
    else {
        candidate[to].students.push_back(std::move(record));
        auto& students = candidate[from].students;
        students.erase(students.begin() + static_cast<std::ptrdiff_t>(index));
    }
    commit(std::move(candidate), nextId_);
}

void Database::deleteStudent(const std::string& code, int id) {
    auto candidate = groups_;
    auto& found = candidate[groupIndex(candidate, code)];
    auto index = studentIndex(found, id);
    found.students.erase(found.students.begin() + static_cast<std::ptrdiff_t>(index));
    commit(std::move(candidate), nextId_);
}
} // namespace studbook
