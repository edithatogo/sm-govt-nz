import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DiskSpaceCheck:
    path: str
    free_bytes: int
    required_bytes: int

    @property
    def ok(self) -> bool:
        return self.free_bytes >= self.required_bytes

    @property
    def free_mb(self) -> float:
        return self.free_bytes / 1024 / 1024

    @property
    def required_mb(self) -> float:
        return self.required_bytes / 1024 / 1024


def check_disk_space(path: str | Path = ".", *, required_mb: int = 100) -> DiskSpaceCheck:
    resolved_path = Path(path).resolve()
    usage = shutil.disk_usage(resolved_path)
    return DiskSpaceCheck(
        path=str(resolved_path),
        free_bytes=usage.free,
        required_bytes=required_mb * 1024 * 1024,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail fast when local disk space is too low.")
    parser.add_argument("--path", default=".")
    parser.add_argument("--required-mb", type=int, default=100)
    args = parser.parse_args()

    result = check_disk_space(args.path, required_mb=args.required_mb)
    print(
        f"disk_space path={result.path} free_mb={result.free_mb:.1f} "
        f"required_mb={result.required_mb:.1f}"
    )
    if not result.ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
