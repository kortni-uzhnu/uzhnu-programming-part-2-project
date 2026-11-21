#ifndef STUDBOOK_CONSOLE_HPP
#define STUDBOOK_CONSOLE_HPP
#include "database.hpp"
#include <iosfwd>

namespace studbook {
void runConsole(Database& database, std::istream& input, std::ostream& output);
}
#endif
