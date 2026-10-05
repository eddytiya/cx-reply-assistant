"""Build frontend assets for Render's native Python web service."""
from pathlib import Path
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
frontend = ROOT / "frontend"
npm = shutil.which("npm.cmd" if os.name == "nt" else "npm")
if npm is None:
    raise RuntimeError("Node.js and npm are required to build the frontend")
subprocess.run([npm, "ci"], cwd=frontend, check=True, shell=os.name == "nt")
subprocess.run([npm, "run", "build"], cwd=frontend, check=True, shell=os.name == "nt")
shutil.copytree(frontend / "dist", ROOT / "backend" / "static", dirs_exist_ok=True)
print("React production files copied to backend/static.")
