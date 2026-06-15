"""Fix the FakeRunner rev-parse matching to work with any branch."""
import pathlib

fp = pathlib.Path(__file__).parent / "tests" / "test_validate_git_mirrors.py"
text = fp.read_text()

old = '        if args[:3] == ["git", "rev-parse", "master"]:'
new = '        if len(args) >= 3 and args[:2] == ["git", "rev-parse"]:'

if old in text:
    text = text.replace(old, new)
    fp.write_text(text)
    print("Fixed rev-parse matching in FakeRunner")
else:
    print("Pattern not found - checking file content...")
    import re
    for m in re.finditer(r'if args.*rev-parse.*', text):
        print(f"  Found: {repr(m.group())}")
    print("File may already be fixed")
