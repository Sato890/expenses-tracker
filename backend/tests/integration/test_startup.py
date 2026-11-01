import subprocess
import sys
from pathlib import Path


def test_importing_app_registers_domain_mappings() -> None:
    backend = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from app.main import app; from sqlalchemy.orm import class_mapper; "
            "from app.domain.group import Group; class_mapper(Group)",
        ],
        cwd=backend,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
