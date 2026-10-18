"""Use the actual method_loop checkout without copying or changing it."""

from pathlib import Path
import sys


def use_method_loop(source: Path) -> Path:
    source = source.resolve()
    if not (source / "method_loop" / "__init__.py").is_file():
        raise FileNotFoundError(f"No method_loop package in {source}")
    sys.path.insert(0, str(source))
    import method_loop

    loaded = Path(method_loop.__file__).resolve().parent
    if loaded != source / "method_loop":
        raise RuntimeError(f"method_loop was already loaded from {loaded}")
    return loaded
