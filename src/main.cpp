#include "console.hpp"
#include <exception>
#include <iostream>
#include <string>

int main(int argc, char* argv[]) {
    if (argc > 2 || (argc == 2 && std::string(argv[1]) == "--help")) {
        std::cout << "Usage: studbook [data-file]\n"
                  << "Default data file: students_data.txt in the current directory.\n";
        return argc > 2 ? 1 : 0;
    }
    try {
        studbook::Database database(argc == 2 ? argv[1] : "students_data.txt");
        database.load();
        studbook::runConsole(database, std::cin, std::cout);
    } catch (const std::exception& error) {
        std::cerr << "Cannot open database: " << error.what()
                  << "\nThe existing data file has not been changed.\n";
        return 1;
    }
    return 0;
}
