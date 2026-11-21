#ifndef STUDBOOK_DATABASE_HPP
#define STUDBOOK_DATABASE_HPP

#include <filesystem>
#include <string>
#include <vector>

namespace studbook {

struct Student {
    int id = 0;
    std::string name;
    std::string birthDate;
    double averageScore = 0;
    std::string phone;
};

struct Group {
    std::string code;
    int year = 0;
    std::vector<Student> students;
};

void validateGroup(const std::string& code, int year);
void validateStudent(const Student& student);

class Database {
public:
    explicit Database(std::filesystem::path filename);
    void load();
    const std::vector<Group>& groups() const { return groups_; }
    const Group& group(const std::string& code) const;
    const Student& student(const std::string& code, int id) const;
    std::size_t studentCount() const;
    void addGroup(const std::string& code, int year);
    void editGroup(const std::string& code, const std::string& newCode, int year);
    void deleteGroup(const std::string& code);
    int addStudent(const std::string& code, Student record);
    void editStudent(const std::string& code, int id,
                     const std::string& destination, Student record);
    void deleteStudent(const std::string& code, int id);

private:
    std::filesystem::path filename_;
    std::vector<Group> groups_;
    int nextId_ = 1;
    void commit(std::vector<Group> candidate, int nextId);
};

} // namespace studbook
#endif
