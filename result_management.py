"""Campus Results: a small, privacy-aware student results manager."""

from __future__ import annotations

import csv
import os
import sys
from pathlib import Path


DATA_FILE = Path(__file__).with_name("campus_results.csv")


class ConsoleStyle:
    """Color terminal output when the current console supports ANSI colors."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    CYAN = "\033[36m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"

    def __init__(self) -> None:
        self.enabled = self._enable_colors()

    @staticmethod
    def _enable_colors() -> bool:
        if "NO_COLOR" in os.environ or os.environ.get("TERM", "").casefold() == "dumb":
            return False
        if not sys.stdout.isatty():
            return False
        if os.name == "nt":
            try:
                import ctypes

                kernel = ctypes.windll.kernel32
                handle = kernel.GetStdHandle(-11)
                mode = ctypes.c_uint()
                if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
                    return False
                if not kernel.SetConsoleMode(handle, mode.value | 0x0004):
                    return False
            except (AttributeError, OSError):
                return False
        return True

    def paint(self, text: str, color: str) -> str:
        if not self.enabled:
            return text
        return f"{color}{text}{self.RESET}"

    def grade(self, mark: float) -> str:
        if mark >= 80:
            return self.GREEN
        if mark >= 70:
            return self.CYAN
        if mark >= 60:
            return self.BLUE
        if mark >= 50:
            return self.YELLOW
        return self.RED


STYLE = ConsoleStyle()


class CourseResult:
    """A student's mark for one course, scored from 0 to 100."""

    def __init__(self, course_name: str, mark: float) -> None:
        course_name = course_name.strip()
        if not course_name:
            raise ValueError("Course name cannot be blank.")
        if not 0 <= float(mark) <= 100:
            raise ValueError("A mark must be between 0 and 100.")
        self.course_name = course_name
        self.mark = float(mark)

    def display_info(self) -> str:
        grade = ResultManagementSystem.grade_for(self.mark)
        return f"{self.course_name:<30} {self.mark:>5.1f}%   {STYLE.paint(grade, STYLE.grade(self.mark))}"


class Student:
    """A student profile and the course results connected to it."""

    def __init__(self, student_id: str, full_name: str, programme: str) -> None:
        student_id = student_id.strip().upper()
        full_name = full_name.strip()
        programme = programme.strip()
        if not student_id or not full_name or not programme:
            raise ValueError("Student ID, name, and programme are all required.")
        self.student_id = student_id
        self.full_name = full_name
        self.programme = programme
        self.results: list[CourseResult] = []

    def add_result(self, result: CourseResult) -> None:
        """Add a course result, or replace the existing result for that course."""
        for index, existing in enumerate(self.results):
            if existing.course_name.casefold() == result.course_name.casefold():
                self.results[index] = result
                return
        self.results.append(result)

    def update_result(self, course_name: str, new_mark: float) -> bool:
        """Update an existing course result; return False if it is not found."""
        for index, result in enumerate(self.results):
            if result.course_name.casefold() == course_name.strip().casefold():
                self.results[index] = CourseResult(result.course_name, new_mark)
                return True
        return False

    def average_mark(self) -> float | None:
        if not self.results:
            return None
        return sum(result.mark for result in self.results) / len(self.results)

    def display_info(self) -> str:
        average = self.average_mark()
        average_text = "No results" if average is None else STYLE.paint(
            f"{average:.1f}% ({ResultManagementSystem.grade_for(average)})", STYLE.grade(average)
        )
        return f"{self.student_id:<12} {self.full_name:<25} {self.programme:<25} {average_text}"


class ResultManagementSystem:
    """Manage student records and save each change to a local CSV file."""

    def __init__(self, institution: str = "Campus Results", data_file: Path = DATA_FILE) -> None:
        self.institution = institution
        # Lists are the single collection type used for groups of records.
        self.students: list[Student] = []
        self.data_file = Path(data_file)
        self.load()

    @classmethod
    def create_demo(cls, data_file: Path = DATA_FILE) -> ResultManagementSystem:
        """Create a ready-to-explore system with fictional demonstration data."""
        system = cls("Campus Results | Demonstration", data_file)
        system.students.clear()
        system.add_student(Student("SL-2601", "Aminata Koroma", "Software Engineering"), save=False)
        system.add_student(Student("SL-2602", "Ibrahim Sesay", "Information Systems"), save=False)
        system.record_result("SL-2601", CourseResult("Programming Fundamentals", 86), save=False)
        system.record_result("SL-2601", CourseResult("Mathematics for Computing", 78), save=False)
        system.record_result("SL-2602", CourseResult("Programming Fundamentals", 72), save=False)
        system.record_result("SL-2602", CourseResult("Digital Literacy", 91), save=False)
        system.save()
        return system

    @staticmethod
    def grade_for(mark: float) -> str:
        """Return the example grade band for a mark out of 100."""
        if mark >= 80:
            return "A - Excellent"
        if mark >= 70:
            return "B - Very good"
        if mark >= 60:
            return "C - Good"
        if mark >= 50:
            return "D - Pass"
        return "F - Needs support"

    def load(self) -> None:
        """Load CSV rows into Student and CourseResult objects."""
        if not self.data_file.exists():
            return
        restored_students: list[Student] = []
        try:
            with self.data_file.open("r", newline="", encoding="utf-8") as file:
                reader = csv.reader(file)
                header = next(reader, [])
                if header != ["student_id", "full_name", "programme", "course_name", "mark"]:
                    raise ValueError("The data file has an unexpected header.")
                for row_number, row in enumerate(reader, start=2):
                    if len(row) != 5:
                        raise ValueError(f"Invalid data on CSV row {row_number}.")
                    student_id, full_name, programme, course_name, mark_text = row
                    student = None
                    for existing in restored_students:
                        if existing.student_id == student_id:
                            student = existing
                            break
                    if student is None:
                        student = Student(student_id, full_name, programme)
                        restored_students.append(student)
                    if course_name:
                        student.add_result(CourseResult(course_name, float(mark_text)))
        except (OSError, ValueError, csv.Error) as error:
            print(STYLE.paint(f"\n  Could not load {self.data_file.name}: {error}", STYLE.RED))
            print(STYLE.paint("  The existing file has been left untouched.", STYLE.YELLOW))
            return
        self.students = restored_students

    def save(self) -> None:
        """Write records atomically so a partial save cannot replace the file."""
        temporary_file = self.data_file.with_suffix(self.data_file.suffix + ".tmp")
        try:
            self.data_file.parent.mkdir(parents=True, exist_ok=True)
            with temporary_file.open("w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["student_id", "full_name", "programme", "course_name", "mark"])
                for student in self.students:
                    if student.results:
                        for result in student.results:
                            writer.writerow([student.student_id, student.full_name, student.programme,
                                             result.course_name, f"{result.mark:.2f}"])
                    else:
                        writer.writerow([student.student_id, student.full_name, student.programme, "", ""])
            os.replace(temporary_file, self.data_file)
        except OSError as error:
            if temporary_file.exists():
                temporary_file.unlink()
            raise OSError(f"Could not save records: {error}") from error

    def add_student(self, student: Student, save: bool = True) -> None:
        if self.find_student(student.student_id) is not None:
            raise ValueError(f"Student ID {student.student_id} is already registered.")
        self.students.append(student)
        if save:
            self.save()

    def find_student(self, student_id: str) -> Student | None:
        normalized_id = student_id.strip().upper()
        for student in self.students:
            if student.student_id == normalized_id:
                return student
        return None

    def search_students(self, search_text: str) -> list[Student]:
        """Find students by ID, name, or programme, ignoring letter case."""
        query = search_text.strip().casefold()
        matches: list[Student] = []
        for student in self.students:
            if (query in student.student_id.casefold()
                    or query in student.full_name.casefold()
                    or query in student.programme.casefold()):
                matches.append(student)
        return matches

    def record_result(self, student_id: str, result: CourseResult, save: bool = True) -> None:
        student = self.find_student(student_id)
        if student is None:
            raise ValueError(f"No student was found with ID {student_id.strip().upper()}.")
        student.add_result(result)
        if save:
            self.save()

    def update_result(self, student_id: str, course_name: str, mark: float) -> bool:
        student = self.find_student(student_id)
        if student is None:
            raise ValueError(f"No student was found with ID {student_id.strip().upper()}.")
        updated = student.update_result(course_name, mark)
        if updated:
            self.save()
        return updated

    def display_students(self, students: list[Student] | None = None) -> None:
        selected_students = self.students if students is None else students
        if not selected_students:
            print(STYLE.paint("\n  No matching student records. Add a student to get started.", STYLE.YELLOW))
            return
        print(STYLE.paint("\n  STUDENT REGISTER", STYLE.BOLD + STYLE.CYAN))
        print(STYLE.paint("  " + "-" * 94, STYLE.DIM))
        print(STYLE.paint(f"  {'STUDENT ID':<12} {'STUDENT':<25} {'PROGRAMME':<25} AVERAGE", STYLE.BOLD))
        print(STYLE.paint("  " + "-" * 94, STYLE.DIM))
        for student in selected_students:
            print("  " + student.display_info())

    def display_report(self, student_id: str) -> None:
        student = self.find_student(student_id)
        if student is None:
            print(STYLE.paint(f"\n  No student was found with ID {student_id.strip().upper()}.", STYLE.RED))
            return
        print(STYLE.paint("\n  STUDENT RESULT REPORT", STYLE.BOLD + STYLE.CYAN))
        print(STYLE.paint("  " + "-" * 65, STYLE.DIM))
        print(f"  {STYLE.paint('Student', STYLE.BOLD)}    {student.full_name} ({STYLE.paint(student.student_id, STYLE.CYAN)})")
        print(f"  {STYLE.paint('Programme', STYLE.BOLD)}  {student.programme}")
        print(STYLE.paint("  " + "-" * 65, STYLE.DIM))
        if not student.results:
            print(STYLE.paint("  No course results have been recorded.", STYLE.YELLOW))
        else:
            for result in student.results:
                print("  " + result.display_info())
            average = student.average_mark()
            print(STYLE.paint("  " + "-" * 65, STYLE.DIM))
            average_summary = f"{average:.1f}%   {self.grade_for(average)}"
            print(f"  {STYLE.paint('Overall average:', STYLE.BOLD)} "
                  f"{STYLE.paint(average_summary, STYLE.grade(average))}")

    def display_dashboard(self) -> None:
        course_count = sum(len(student.results) for student in self.students)
        graded_students = 0
        for student in self.students:
            if student.average_mark() is not None:
                graded_students += 1
        overall_average = None
        if course_count:
            overall_average = sum(result.mark for student in self.students for result in student.results) / course_count
        print(STYLE.paint("\n  CAMPUS SNAPSHOT", STYLE.BOLD + STYLE.CYAN))
        print(STYLE.paint("  " + "-" * 42, STYLE.DIM))
        print(f"  Registered students   {len(self.students)}")
        print(f"  Students with results {graded_students}")
        print(f"  Course results stored {course_count}")
        if overall_average is None:
            print("  Average mark          No results yet")
        else:
            average_text = f"{overall_average:.1f}%"
            print(f"  Average mark          {STYLE.paint(average_text, STYLE.grade(overall_average))}")
        print(f"  Data file             {STYLE.paint(self.data_file.name, STYLE.DIM)}")


def read_required(prompt: str) -> str:
    """Read a non-empty value, with a short explanation when blank."""
    while True:
        value = input(STYLE.paint(prompt, STYLE.CYAN)).strip()
        if value:
            return value
        print(STYLE.paint("  Please enter a value; it cannot be blank.", STYLE.YELLOW))


def read_mark(prompt: str = "  Mark (0-100): ") -> float:
    while True:
        try:
            mark = float(input(STYLE.paint(prompt, STYLE.CYAN)).strip())
            if 0 <= mark <= 100:
                return mark
            print(STYLE.paint("  Enter a mark from 0 to 100.", STYLE.YELLOW))
        except ValueError:
            print(STYLE.paint("  Enter a number, for example 78 or 82.5.", STYLE.YELLOW))


def show_menu() -> None:
    border = "  +--------------------------------------------------+"
    print("\n" + STYLE.paint(border, STYLE.CYAN))
    print(STYLE.paint("  |                 CAMPUS RESULTS                   |", STYLE.BOLD + STYLE.CYAN))
    print(STYLE.paint("  |          Student Records and Gradebook           |", STYLE.CYAN))
    print(STYLE.paint(border, STYLE.CYAN))
    options = [
        ("1", "Add a student"),
        ("2", "Record a course result"),
        ("3", "Edit an existing result"),
        ("4", "View all students"),
        ("5", "View a student report"),
        ("6", "Search students"),
        ("7", "View campus dashboard"),
        ("8", "Load fictional demo records"),
        ("0", "Save and exit"),
    ]
    for number, label in options:
        print("  |  " + STYLE.paint(number, STYLE.YELLOW + STYLE.BOLD) + "  " + label.ljust(45) + "|")
    print(STYLE.paint(border, STYLE.CYAN))


def main() -> None:
    system = ResultManagementSystem()
    print("\n" + STYLE.paint("  Welcome to Campus Results", STYLE.BOLD + STYLE.CYAN))
    print(STYLE.paint("  Local student register, course gradebook, and reports", STYLE.DIM))
    print(f"  {STYLE.paint(str(len(system.students)), STYLE.GREEN)} student record(s) loaded from "
          f"{STYLE.paint(system.data_file.name, STYLE.CYAN)}.")
    while True:
        show_menu()
        choice = input(STYLE.paint("\n  Choose an option: ", STYLE.BOLD + STYLE.YELLOW)).strip()
        if choice == "1":
            print(STYLE.paint("\n  ADD STUDENT", STYLE.BOLD + STYLE.MAGENTA))
            try:
                student = Student(
                    read_required("  Student ID: "),
                    read_required("  Full name: "),
                    read_required("  Programme: "),
                )
                system.add_student(student)
                print(STYLE.paint(f"\n  Student added: {student.full_name} ({student.student_id}).", STYLE.GREEN))
                print(STYLE.paint(f"  Saved to {system.data_file.name}; the record will be here next time.", STYLE.DIM))
            except (ValueError, OSError) as error:
                print(STYLE.paint(f"\n  Could not add student: {error}", STYLE.RED))
        elif choice == "2":
            print(STYLE.paint("\n  RECORD COURSE RESULT", STYLE.BOLD + STYLE.MAGENTA))
            student_id = read_required("  Student ID: ")
            course_name = read_required("  Course name: ")
            mark = read_mark()
            try:
                student = system.find_student(student_id)
                had_result = student is not None and any(
                    item.course_name.casefold() == course_name.casefold() for item in student.results
                )
                system.record_result(student_id, CourseResult(course_name, mark))
                action = "updated" if had_result else "recorded"
                print(STYLE.paint(f"  Result {action} and saved.", STYLE.GREEN) + " Grade: "
                      + STYLE.paint(system.grade_for(mark), STYLE.grade(mark)) + ".")
            except (ValueError, OSError) as error:
                print(STYLE.paint(f"  Could not record result: {error}", STYLE.RED))
        elif choice == "3":
            print(STYLE.paint("\n  EDIT RESULT", STYLE.BOLD + STYLE.MAGENTA))
            student_id = read_required("  Student ID: ")
            student = system.find_student(student_id)
            if student is None:
                print(STYLE.paint(f"  No student was found with ID {student_id.strip().upper()}.", STYLE.RED))
            elif not student.results:
                print(STYLE.paint("  This student has no results to edit yet.", STYLE.YELLOW))
            else:
                system.display_report(student_id)
                course_name = read_required("\n  Course to edit: ")
                new_mark = read_mark("  New mark (0-100): ")
                try:
                    if system.update_result(student_id, course_name, new_mark):
                        print(STYLE.paint("  Result updated and saved.", STYLE.GREEN) + " New grade: "
                              + STYLE.paint(system.grade_for(new_mark), STYLE.grade(new_mark)) + ".")
                    else:
                        print(STYLE.paint("  That course was not found. Choose a course shown in the report.", STYLE.YELLOW))
                except OSError as error:
                    print(STYLE.paint(f"  Could not save the change: {error}", STYLE.RED))
        elif choice == "4":
            system.display_students()
        elif choice == "5":
            system.display_report(read_required("\n  Student ID: "))
        elif choice == "6":
            query = read_required("\n  Search by student ID, name, or programme: ")
            system.display_students(system.search_students(query))
        elif choice == "7":
            system.display_dashboard()
        elif choice == "8":
            answer = input("  Replace the current records with fictional demo records? (y/n): ").strip().casefold()
            if answer == "y":
                try:
                    system = ResultManagementSystem.create_demo(system.data_file)
                    print(STYLE.paint("  Demo records loaded and saved. Use option 8 again to replace them.", STYLE.GREEN))
                except OSError as error:
                    print(STYLE.paint(f"  Could not save the demo records: {error}", STYLE.RED))
            else:
                print(STYLE.paint("  No records were changed.", STYLE.DIM))
        elif choice == "0":
            try:
                system.save()
                print(STYLE.paint(f"\n  All changes are saved in {system.data_file.name}. Goodbye!\n", STYLE.GREEN))
                break
            except OSError as error:
                print(STYLE.paint(f"\n  Could not save before exit: {error}", STYLE.RED))
                answer = input("  Exit anyway and risk losing recent changes? (y/n): ").strip().casefold()
                if answer == "y":
                    break
        else:
            print(STYLE.paint("\n  Choose one of the options shown above.", STYLE.YELLOW))


if __name__ == "__main__":
    main()
