import unittest
from conans.test.utils.cpp_test_files import cpp_hello_conan_files
from conans.test.utils.tools import TestClient
from nose.plugins.attrib import attr


@attr('slow')
class CMakeFindPathGeneratorTest(unittest.TestCase):

    def cmake_find_package_system_libs_test(self):
        conanfile = """from conans import ConanFile, tools
class Test(ConanFile):
    name = "Test"
    version = "0.1"

    def package_info(self):
        self.cpp_info.libs.append("fake_lib")
    """
        client = TestClient()
        client.save({"conanfile.py": conanfile})
        client.run("export . user/channel")

        conanfile = """from conans import ConanFile, tools, CMake
class Consumer(ConanFile):
    name = "consumer"
    version = "0.1"
    requires = "Test/0.1@user/channel"
    generators = "cmake_find_package"
    exports_sources = "CMakeLists.txt"

    def build(self):
        cmake = CMake(self)
        cmake.configure()

    """
        cmakelists = """
project(consumer)
cmake_minimum_required(VERSION 3.1)
find_package(Test)
message("Libraries to Link: ${Test_LIBS}")

get_target_property(tmp Test::Test INTERFACE_LINK_LIBRARIES)
message("Target libs: ${tmp}")
"""
        client.save({"conanfile.py": conanfile, "CMakeLists.txt": cmakelists})
        client.run("create . user/channel --build missing")
        self.assertIn("Library fake_lib not found in package, might be system one", client.out)
        self.assertIn("Libraries to Link: fake_lib", client.out)
        self.assertIn("Target libs: fake_lib", client.out)

    def cmake_find_package_test(self):
        """First package without custom find_package"""
        client = TestClient()
        files = cpp_hello_conan_files(name="Hello0",
                                      settings='"os", "compiler", "arch", "build_type"')
        client.save(files)
        client.run("create . user/channel -s build_type=Release")

        # Consume the previous Hello0 with auto generated FindHello0.cmake
        # The module path will point to the "install" folder automatically (CMake helper)
        files = cpp_hello_conan_files(name="Hello1", deps=["Hello0/0.1@user/channel"],
                                      settings='"os", "compiler", "arch", "build_type"')
        files["conanfile.py"] = files["conanfile.py"].replace(
            'generators = "cmake", "gcc"',
            'generators = "cmake_find_package"')
        files["CMakeLists.txt"] = """
set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
project(MyHello CXX)
cmake_minimum_required(VERSION 2.8)

find_package(Hello0 REQUIRED)

add_library(helloHello1 hello.cpp)
target_link_libraries(helloHello1 PUBLIC Hello0::Hello0)
add_executable(say_hello main.cpp)
target_link_libraries(say_hello helloHello1)

"""
        client.save(files, clean_first=True)
        client.run("create . user/channel -s build_type=Release")
        self.assertIn("Conan: Using autogenerated FindHello0.cmake", client.out)

        # Now link with old cmake
        files["CMakeLists.txt"] = """
set(CMAKE_VERSION "2.8")
set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
project(MyHello CXX)
cmake_minimum_required(VERSION 2.8)
message(${CMAKE_BINARY_DIR})
set(CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR} ${CMAKE_MODULE_PATH})

find_package(Hello0 REQUIRED)

add_library(helloHello1 hello.cpp)

if(NOT DEFINED Hello0_FOUND)
    message(FATAL_ERROR "Hello0_FOUND not declared")
endif()
if(NOT DEFINED Hello0_INCLUDE_DIRS)
    message(FATAL_ERROR "Hello0_INCLUDE_DIRS not declared")
endif()
if(NOT DEFINED Hello0_INCLUDES)
    message(FATAL_ERROR "Hello0_INCLUDES not declared")
endif()
if(NOT DEFINED Hello0_LIBRARIES)
    message(FATAL_ERROR "Hello0_LIBRARIES not declared")
endif()

include_directories(${Hello0_INCLUDE_DIRS})
target_link_libraries(helloHello1 PUBLIC ${Hello0_LIBS})
add_executable(say_hello main.cpp)
target_link_libraries(say_hello helloHello1)

"""
        client.save(files, clean_first=True)
        client.run("create . user/channel -s build_type=Release")
        self.assertIn("Conan: Using autogenerated FindHello0.cmake", client.out)

        # Now a transitive consumer, but the consumer only find_package the first level Hello1
        files = cpp_hello_conan_files(name="Hello2", deps=["Hello1/0.1@user/channel"],
                                      settings='"os", "compiler", "arch", "build_type"')
        files["CMakeLists.txt"] = """
set(CMAKE_CXX_COMPILER_WORKS 1)
set(CMAKE_CXX_ABI_COMPILED 1)
project(MyHello CXX)
cmake_minimum_required(VERSION 2.8)
set(CMAKE_MODULE_PATH ${CMAKE_BINARY_DIR} ${CMAKE_MODULE_PATH})
find_package(Hello1 REQUIRED) # We don't need to find Hello0, it is transitive

add_library(helloHello2 hello.cpp)
target_link_libraries(helloHello2 PUBLIC Hello1::Hello1)

add_executable(say_hello main.cpp)
target_link_libraries(say_hello helloHello2)
        """
        files["conanfile.py"] = files["conanfile.py"].replace(
            'generators = "cmake", "gcc"',
            'generators = "cmake_find_package"')
        client.save(files, clean_first=True)
        client.run("create . user/channel -s build_type=Release")
        self.assertIn("Conan: Using autogenerated FindHello0.cmake", client.out)
        self.assertIn("Conan: Using autogenerated FindHello1.cmake", client.out)
