#include <iostream>
#include <string>
#include "arsc_resolver.cpp"

int main(int argc, char** argv) {
    if (argc != 3) return 2;
    std::string selected;
    if (!oh_adapter::ResolveResourceIdToFile(argv[1], std::stoul(argv[2], nullptr, 0), selected)) {
        std::cout << "MISSING\n";
        return 0;
    }
    std::cout << "SELECTED\t" << selected << "\n";
    return 0;
}
