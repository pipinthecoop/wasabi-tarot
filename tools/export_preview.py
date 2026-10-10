"""Create a self-contained, network-free illustrated demo from the production UI."""

import base64
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def data_url(path: Path) -> str:
    mime = "image/webp" if path.suffix == ".webp" else "image/png"
    return "data:" + mime + ";base64," + base64.b64encode(path.read_bytes()).decode()


def main():
    css = (ROOT / "web/table.css").read_text()
    js = (ROOT / "web/table.js").read_text()
    html = (ROOT / "web/table.html").read_text()
    for name in ("header", "card-back", "stone-button"):
        uri = data_url(ROOT / "art/theme" / (name + ".webp"))
        css = css.replace("/assets/theme/" + name + ".webp", uri)
        js = js.replace("/assets/theme/" + name + ".webp", uri)
    front_art = {}
    for deck in ("dawn", "midnight"):
        for art in (ROOT / "art" / deck).glob("*.png"):
            front_art["/assets/decks/" + deck + "/" + art.name] = data_url(art)
    js = "const previewArt = " + json.dumps(front_art) + ";\n" + js
    js = js.replace("art.src = card.art &&", "art.src = previewArt[card.art] || (card.art &&")
    js = js.replace(" : 'data:image/webp;base64,", " : 'data:image/webp;base64,")
    # Close the extra parenthesis at the end of the source assignment.
    lines = js.splitlines()
    for index, line in enumerate(lines):
        if "art.src = previewArt[card.art]" in line:
            lines[index] = line[:-1] + ");"
    js = "\n".join(lines)
    js = js.replace("registry = await (await fetch('/web/demo.json')).json();", "registry = " + (ROOT / "web/demo.json").read_text().strip() + ";")
    js = js.replace("} else { await refreshLive(); }", "} else { /* standalone demo: no server calls */ }")
    js = js.replace("const embedded = location.pathname.startsWith('/embed/');", "const embedded = false;")
    # Live login is intentionally unavailable in this downloadable artifact.
    begin = js.index("$('login-form').addEventListener('submit'")
    end = js.index("async function init()", begin)
    js = js[:begin] + "$('login-form').addEventListener('submit', e => e.preventDefault());\n" + js[end:]
    html = html.replace('<link rel="stylesheet" href="/web/table.css">', "<style>" + css + "</style>")
    html = html.replace('<script src="/web/table.js" defer></script>', "")
    html = html.replace("</body>", "<script>" + js + "</script></body>")
    html = html.replace("Connect Slack table", "About live setup")
    html = html.replace('id="login-code" type="password"', 'id="login-code" disabled type="password"')
    html = html.replace('class="stone-button" type="submit"><span>Enter the parlor', 'class="stone-button" disabled type="submit"><span>Preview only')
    html = html.replace(
        '<p id="login-error" role="alert"></p>',
        '<p id="login-error" role="alert">This downloadable demo has no live login. Wasabi must configure the hosted service before connecting a Slack table.</p>',
    )
    html = html.replace('href="/table"', 'href="#"')
    path = Path(sys.argv[1])
    path.write_text(html)
    print(path)


if __name__ == "__main__":
    main()
