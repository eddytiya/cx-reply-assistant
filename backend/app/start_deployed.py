"""Initialize the demo database before starting the hosted application."""
import os
import subprocess
import sys

import uvicorn


def main():
    for module, args in (
        ("alembic", ["upgrade", "head"]),
        ("app.seed", []),
        ("app.seed_scenarios", []),
        ("app.seed_admin", []),
    ):
        subprocess.run([sys.executable, "-m", module, *args], check=True)
    uvicorn.run("app.deployed:app", host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


if __name__ == "__main__":
    main()
