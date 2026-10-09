"""PyInstaller entry point.

athc's `main()` lives in the `athc.cli` package, which has no `__main__`
guard, so the frozen build needs a script that calls it.
"""

from athc.cli import main

main()
