"""`python -m ogdf` - print the installation diagnostic report."""

import sys

from ogdf._about import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
