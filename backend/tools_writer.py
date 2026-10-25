import sys
import pathlib

def write_file(dest, content):
    p = pathlib.Path(dest)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding='utf-8')
    print(f"Wrote {dest} ({len(content)} chars)")

if __name__ == "__main__":
    dest = sys.argv[1]
    content = sys.stdin.read()
    write_file(dest, content)
