import sys
from pathlib import Path

# The converters are standalone scripts (not a package), so make the repo
# root importable for tests that `import convert_tautulli_to_simkl` etc.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
