"""Check pinned requirements against PyPI for Python 3.11 compatibility."""
import json
import sys
import urllib.error
import urllib.request

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import Version

TARGET_PYTHON = Version("3.11")  # fixed target, independent of the running interpreter
CANDIDATES = [Version(f"2.{m}") for m in range(8)] + [Version(f"3.{m}") for m in range(30)]


def fetch_json(url):
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def min_python(spec):
    """Lowest Python minor version allowed by the specifier, or None."""
    for v in CANDIDATES:
        if spec.contains(v, prereleases=True):
            return v
    return None


def main(path):
    with open(path) as f:
        lines = [l.strip() for l in f if l.strip() and not l.strip().startswith("#")]

    not_found = 0
    incompatible = 0
    highest = None  # (min_version, "name==version")

    for line in lines:
        name, _, version = line.partition("==")
        name, version = name.strip(), version.strip()

        if fetch_json(f"https://pypi.org/pypi/{name}/json") is None:
            not_found += 1
            continue
        release = fetch_json(f"https://pypi.org/pypi/{name}/{version}/json")
        if release is None:
            not_found += 1
            continue

        requires = (release["info"].get("requires_python") or "").strip()
        if not requires:
            continue  # no requires_python -> compatible
        try:
            spec = SpecifierSet(requires)
        except InvalidSpecifier:
            continue

        if not spec.contains(TARGET_PYTHON, prereleases=True):
            incompatible += 1

        low = min_python(spec)
        if low is not None and (highest is None or low > highest[0]):
            highest = (low, f"{name}=={version}")

    print(f"Dependencies checked : {len(lines)}")
    print(f"Not found on PyPI:{not_found}")
    print(f"Incompatible with Python 3.11: {incompatible}")
    if highest:
        print(f"Highest requirement: {highest[1]} (>={highest[0]})")
    else:
        print("Highest requirement: none")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "requirements.txt")
