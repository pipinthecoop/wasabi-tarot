"""Package reviewed public changes over the known published commit, no credentials."""

import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = "f820935bb22531c6bea048c0deec31af60bdbff2"


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def main():
    assert git("rev-parse", "HEAD").decode().strip() == BASE, "Review publication base before packaging"
    original = json.loads(git("show", f"{BASE}:registry.json"))
    current = json.loads((ROOT / "registry.json").read_text())
    assert current["cards"] == original["cards"], "Do not alter existing canonical card records"
    assert all(current["decks"][deck] == spec for deck, spec in original["decks"].items())
    assert current["decks"]["crt"]["cards"] == original["decks"]["dawn"]["cards"]
    for directory in ("art/dawn", "art/midnight"):
        assert not git("diff", BASE, "--", directory), "Existing artwork changed"
    changed = git("diff", "--name-only", BASE).decode().splitlines()
    untracked = git("ls-files", "--others", "--exclude-standard").decode().splitlines()
    allowed = {
        ".dockerignore",
        ".env.example",
        "MANIFEST.in",
        "README.md",
        "CRT-HANDOFF.md",
        "HOSTING-RUNBOOK.md",
        "registry.json",
        "theme.json",
        "tarot/server.py",
        "tarot/core.py",
        "tarot/preview_server.py",
        "tests/test_hosting.py",
        "pyproject.toml",
        "tools/export_preview.py",
        "web/demo.json",
        "web/table.js",
        "web/table.html",
        "web/table.css",
        "tests/test_crt.py",
        "tools/generate_crt.py",
        "tools/crt_catalogue.py",
        "tools/crt_ascii_deck.py",
        "tools/crt_ascii_studies.py",
        "tools/animate_crt.py",
        "tools/animate_crt_surface.py",
        "tools/crt_motion_regions.py",
        "tools/crt_surface_samples.py",
        "tools/gif_gallery.py",
        "tools/render_crt.py",
        "tools/qa_crt.py",
        "tools/package_crt.py",
        "art/theme/crt-back.png",
        "art/theme/crt-back.webp",
    }
    files = sorted(set(changed + untracked))
    files = [
        p
        for p in files
        if p in allowed or (p.startswith("art/crt/") and Path(p).name != "animation-samples.json" and Path(p).suffix in (".svg", ".png", ".gif", ".json"))
    ]
    entries = []
    for path in files:
        blob = (ROOT / path).read_bytes()
        base_blob = subprocess.run(["git", "show", f"{BASE}:{path}"], cwd=ROOT, capture_output=True)
        entries.append(
            {
                "path": path,
                "size": len(blob),
                "sha256": hashlib.sha256(blob).hexdigest(),
                "base_sha256": hashlib.sha256(base_blob.stdout).hexdigest() if base_blob.returncode == 0 else None,
            }
        )
    manifest = {
        "repository": "pipinthecoop/wasabi-tarot",
        "base_commit": BASE,
        "files": entries,
        "excluded": ["credentials", "private art", "live databases", "previews", "caches"],
        "apply": "Verify base hashes; add/replace listed files. Preserve concurrent upstream changes. Wasabi owns deployment.",
    }
    output = ROOT / "preview/phosphor-arcana-changes.zip"
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            bundle.write(ROOT / path, path)
        bundle.writestr("CRT-CHANGE-MANIFEST.json", json.dumps(manifest, indent=2) + "\n")
    print(f"{output}: {len(files)} public changed files, {output.stat().st_size} bytes")


if __name__ == "__main__":
    main()
