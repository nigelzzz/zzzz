.PHONY: test clean

# Clean first so that old executables don't mess up the test results.
test: clean
	python3 test.py

clean:
	$(RM) -r assembler_output/ compiler_output/ riscv/ executable/ result/ diff.txt
