#!/usr/bin/env python3

import argparse
import colorama
import subprocess
import sys
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List

DIR = Path(__file__).resolve().parent


class CaseType(Enum):
    OPEN = auto()
    BONUS = auto()
    HIDDEN = auto()


class TestStatus(Enum):
    PASS = auto()
    FAIL = auto()
    SKIP = auto()


@dataclass
class TestCase:
    type: CaseType
    score: float
    name: str


class Grader:
    """
    case_id: TestCase(case_type, score, case_name)
        case_id     Used by the "--case_id" flag to run only one test case
        case_type   The diff of CaseType.HIDDEN is not shown
        score       The max score of the test case
        case_name   The name of the file in "test_cases" and "sample_solutions"
    """
    CASES: Dict[str, TestCase] = {
        "1": TestCase(CaseType.OPEN, 5.0, "01_variable_constant"),
        "2": TestCase(CaseType.OPEN, 5.0, "02_expr"),
        "3": TestCase(CaseType.OPEN, 5.0, "03_function"),
        "4": TestCase(CaseType.OPEN, 5.0, "04_spec_example"),
        "5": TestCase(CaseType.OPEN, 5.0, "05_condition"),
        "6": TestCase(CaseType.OPEN, 5.0, "06_loop"),
        "7": TestCase(CaseType.OPEN, 2.5, "07_advance_condition"),
        "8": TestCase(CaseType.OPEN, 2.5, "08_advance_expr"),
        "9": TestCase(CaseType.OPEN, 2.5, "09_advance_function"),
        "10": TestCase(CaseType.OPEN, 2.5, "10_advance_loop_1"),
        "11": TestCase(CaseType.OPEN, 2.5, "11_advance_loop_2"),
        "12": TestCase(CaseType.OPEN, 2.5, "12_advance_argument"),
        "13": TestCase(CaseType.OPEN, 2.5, "13_advance_negative"),
        "14": TestCase(CaseType.BONUS, 1.0, "14_bonus_boolean_1"),
        "15": TestCase(CaseType.BONUS, 1.0, "15_bonus_boolean_2"),
        "16": TestCase(CaseType.BONUS, 1.5, "16_bonus_array_1"),
        "17": TestCase(CaseType.BONUS, 1.5, "17_bonus_array_2"),
        "18": TestCase(CaseType.BONUS, 1.5, "18_bonus_string"),
        "19": TestCase(CaseType.BONUS, 1.5, "19_bonus_real_1"),
        "20": TestCase(CaseType.BONUS, 1.5, "20_bonus_real_2"),
        "h1": TestCase(CaseType.HIDDEN, 5.0, "h01_variable_constant"),
        "h2": TestCase(CaseType.HIDDEN, 5.0, "h02_expr"),
        "h3": TestCase(CaseType.HIDDEN, 5.0, "h03_function"),
        "h4": TestCase(CaseType.HIDDEN, 5.0, "h04_spec_example"),
        "h5": TestCase(CaseType.HIDDEN, 5.0, "h05_condition"),
        "h6": TestCase(CaseType.HIDDEN, 5.0, "h06_loop"),
        "h7": TestCase(CaseType.HIDDEN, 2.5, "h07_advance_condition"),
        "h8": TestCase(CaseType.HIDDEN, 2.5, "h08_advance_expr"),
        "h9": TestCase(CaseType.HIDDEN, 2.5, "h09_advance_function"),
        "h10": TestCase(CaseType.HIDDEN, 2.5, "h10_advance_loop_1"),
        "h11": TestCase(CaseType.HIDDEN, 2.5, "h11_advance_loop_2"),
        "h12": TestCase(CaseType.HIDDEN, 2.5, "h12_advance_argument"),
        "h13": TestCase(CaseType.HIDDEN, 2.5, "h13_advance_negative"),
        "h14": TestCase(CaseType.HIDDEN, 1.0, "h14_bonus_boolean_1"),
        "h15": TestCase(CaseType.HIDDEN, 1.0, "h15_bonus_boolean_2"),
        "h16": TestCase(CaseType.HIDDEN, 1.5, "h16_bonus_array_1"),
        "h17": TestCase(CaseType.HIDDEN, 1.5, "h17_bonus_array_2"),
        "h18": TestCase(CaseType.HIDDEN, 1.5, "h18_bonus_string"),
        "h19": TestCase(CaseType.HIDDEN, 1.5, "h19_bonus_real_1"),
        "h20": TestCase(CaseType.HIDDEN, 1.5, "h20_bonus_real_2"),
        # Uncomment next line to add a new test case:
        # "my1": TestCase(CaseType.OPEN, 0.0, "my_test_case_1"),
    }

    def __init__(self, executable: Path, io_file_path: Path) -> None:
        self.executable: Path = executable
        self.io_file_path = io_file_path
        self.cases_to_run: list[TestCase] = list(self.CASES.values())
        self.diff_result: str = ""
        self.case_dir: Path = DIR / "test_cases"
        self.solution_dir: Path = DIR / "sample_solutions"
        self.compiler_output_dir: Path = DIR / "compiler_output"
        self.assembler_output_dir: Path = DIR / "assembler_output"
        self.executable_dir: Path = DIR / "executable"
        self.asm_dir: Path = DIR / "riscv"
        self.output_dir: Path = DIR / "result"
        if not self.compiler_output_dir.exists():
            self.compiler_output_dir.mkdir()
        if not self.assembler_output_dir.exists():
            self.assembler_output_dir.mkdir()
        if not self.executable_dir.exists():
            self.executable_dir.mkdir()
        if not self.asm_dir.exists():
            self.asm_dir.mkdir()
        if not self.output_dir.exists():
            self.output_dir.mkdir()

    def find_index_of_last_digit_sequence(self, string: str) -> int:
        """Return `-1` if no digit sequence is found."""
        index: int = len(string)
        for c in reversed(string):
            if not c.isdigit():
                break
            index -= 1
        return index if index < len(string) else -1

    def set_case_id_to_run(self, input_case_id: str) -> None:
        case_id: str = input_case_id
        if case_id not in self.CASES:
            # fuzzy search the test case such as "01", "h01"; remove the prefix "0" of the digit sequence.
            number_at: int = self.find_index_of_last_digit_sequence(input_case_id)
            if number_at != -1:
                prefix: str = input_case_id[:number_at]
                number: int = int(input_case_id[number_at:])
                case_id = f"{prefix}{number}"
        if case_id in self.CASES:
            self.cases_to_run = [self.CASES[case_id]]
        else:
            print(f"ERROR: Invalid case ID {input_case_id}")
            exit(1)

    def execute_process(self, command: List[str], stdin: bytes = b"") -> tuple[int, bytes, bytes]:
        """Returns the exit code, stdout, and stderr of the process."""
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            assert process.stdin is not None
            process.stdin.write(stdin)
            process.stdin.close()
        except Exception as e:
            print(f"Call of '{' '.join(command)}' failed: {e}")
            return 1, b"", b""

        exit_code: int = process.wait()
        assert process.stdout is not None and process.stderr is not None
        stdout: bytes = process.stdout.read()
        stderr: bytes = process.stderr.read()
        return exit_code, stdout, stderr

    def run_test_case(self, case: TestCase) -> TestStatus:
        """Runs the test case and outputs the diff between the result and the solution."""
        case_path: Path = self.case_dir / f"{case.name}.p"
        solution_path: Path = self.solution_dir / f"{case.name}"
        compiler_output_path: Path = self.compiler_output_dir / f"{case.name}"
        assembler_output_path: Path = self.assembler_output_dir / f"{case.name}"
        executable_path: Path = self.executable_dir / f"{case.name}"
        asm_path: Path = self.asm_dir / f"{case.name}.S"
        output_path: Path = self.output_dir / f"{case.name}"

        if not case_path.exists():
            return TestStatus.SKIP

        # Compile to risc-v
        compile_command: List[str] = [str(self.executable), str(case_path), "--save-path", str(self.asm_dir)]
        compile_stdout: bytes
        compile_stderr: bytes
        _, compile_stdout, compile_stderr = self.execute_process(compile_command)
        with compiler_output_path.open("wb") as file:
            file.write(compile_stdout)
            file.write(compile_stderr)

        # Assemble to executable
        assemble_command: List[str] = ["riscv32-unknown-elf-gcc", str(asm_path), str(self.io_file_path), "-o", str(executable_path)]
        assemble_stdout: bytes
        assemble_stderr: bytes
        _, assemble_stdout, assemble_stderr = self.execute_process(assemble_command)
        with assembler_output_path.open("wb") as file:
            file.write(assemble_stdout)
            file.write(assemble_stderr)

        # Run executable
        run_command: List[str] = ["spike", "--isa=rv32gc", "/risc-v/riscv32-unknown-elf/bin/pk", str(executable_path)]
        run_stdout: bytes
        run_stderr: bytes
        _, run_stdout, run_stderr = self.execute_process(run_command, b"123")
        with output_path.open("wb") as file:
            file.write(run_stdout)
            file.write(run_stderr)

        # Diff
        diff_command: List[str] = ["diff", "-Z", "-u", str(output_path), str(solution_path), f"--label=your output:({output_path})", f"--label=answer:({solution_path})"]
        diff_exit_code: int
        diff_stdout: bytes
        diff_exit_code, diff_stdout, _ = self.execute_process(diff_command)
        diff_result: str = diff_stdout.decode("utf-8", errors="replace")
        if diff_exit_code != 0:
            # The header part.
            self.diff_result += f"{case.name}\n"
            # The diff part.
            if not solution_path.exists():
                self.diff_result += "// Solution file not found.\n"
            elif case.type == CaseType.HIDDEN:
                self.diff_result += "// Diff of hidden cases is not shown.\n"
            else:
                self.diff_result += f"{diff_result}\n"
        return TestStatus.PASS if diff_exit_code == 0 else TestStatus.FAIL

    def run(self) -> int:
        total_score: float = 0
        max_score: float = 0
        had_passed_all_visible_cases: bool = True

        print("---\tCase\t\tPoints")
        for case in self.cases_to_run:
            print(f"+++ TESTING {case.type.name.lower()} case {case.name}:")
            status: TestStatus = self.run_test_case(case)
            score: float = 0
            if status is TestStatus.PASS:
                score = case.score
            elif status is TestStatus.FAIL:
                had_passed_all_visible_cases = False

            self.set_text_color(status)
            if status is TestStatus.SKIP:
                print(f"---\t{case.name}\tSKIPPED\t0/{case.score}")
            else:
                print(f"---\t{case.name}\t{score}/{case.score}")
            self.reset_text_color()
            total_score += score
            max_score += case.score

        self.set_text_color(TestStatus.PASS if had_passed_all_visible_cases else TestStatus.FAIL)
        print(f"---\tTOTAL\t\t{total_score}/{max_score}")
        self.reset_text_color()

        with (self.output_dir / "score.txt").open("w") as score_file:
            score_file.write(f"---\tTOTAL\t\t{total_score}/{max_score}")
        with (self.output_dir / "diff.txt").open("w") as diff_file:
            diff_file.write(self.diff_result)

        # NOTE: Return 1 on test failure to support GitHub CI; otherwise, such CI never fails.
        return 0 if had_passed_all_visible_cases else 1

    @staticmethod
    def set_text_color(test_status: TestStatus) -> None:
        """Sets the color based on whether the test has passed or not."""
        if test_status is TestStatus.PASS:
            color = colorama.Fore.GREEN
        elif test_status is TestStatus.FAIL:
            color = colorama.Fore.RED
        else:
            color = colorama.Fore.YELLOW
        print(color, end='')

    @staticmethod
    def reset_text_color() -> None:
        print(colorama.Style.RESET_ALL, end='')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", help="executable to grade", type=Path, default=DIR.parent / "src" / "compiler")
    parser.add_argument("--io_file", help="IO file for io function", type=Path, default=DIR.parent / "test" / "io.c")
    parser.add_argument("--case_id", help="test case's ID", type=str)
    args = parser.parse_args()

    grader = Grader(args.executable, args.io_file)
    if args.case_id is not None:
        grader.set_case_id_to_run(args.case_id)
    return grader.run()


if __name__ == "__main__":
    sys.exit(main())
