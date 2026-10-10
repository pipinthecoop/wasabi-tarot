"""Self-contained independently looping review gallery, with static choice."""

import base64
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDS = [
    "major-0",
    "major-2",
    "major-16",
    "major-10",
    "wands-eight",
    "wands-knight",
    "cups-seven",
    "cups-queen",
    "swords-three",
    "swords-nine",
    "pentacles-eight",
    "pentacles-queen",
]


def main():
    catalogue = json.loads((ROOT / "art/crt/catalogue.json").read_text())["cards"]
    motions = json.loads((ROOT / "art/crt/animations.json").read_text())["cards"]
    cards = {card["id"]: card for card in catalogue}
    specs = {spec["id"]: spec for spec in motions}
    tiles = []
    for cid in IDS:
        png = "data:image/png;base64," + base64.b64encode((ROOT / "art/crt" / f"{cid}.png").read_bytes()).decode()
        gif = "data:image/gif;base64," + base64.b64encode((ROOT / "art/crt" / f"{cid}.gif").read_bytes()).decode()
        tile = (
            f'<figure><img src="{png}" data-static="{png}" data-motion="{gif}" alt="{cards[cid]["name"]}"><figcaption><b>{cards[cid]["name"]}</b><span>'
            + "CRT scan / flicker / bloom"
            + f" / {specs[cid]['duration'] * specs[cid]['frames'] / 1000:.2f}s loop</span></figcaption></figure>"
        )
        tiles.append(tile)
    doc = (
        """<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Phosphor Arcana / Living terminal</title><style>*{box-sizing:border-box}body{margin:0;background:#020704;color:#caffda;font:16px Georgia,serif;padding:30px}header{max-width:1100px;margin:0 auto 30px}h1{font-size:42px;margin:0 0 14px}p{color:#99b3a0;line-height:1.6}button{padding:12px 18px;border:1px solid #6fa986;background:#0c2116;color:#d4ffe2;cursor:pointer;font:inherit;border-radius:8px}main{max-width:1100px;margin:auto;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:22px}figure{margin:0}img{width:100%;height:auto;border-radius:12px}figcaption{padding:12px 4px}b{font-size:18px}span{display:block;color:#739b80;font:11px monospace;margin-top:9px}@media(max-width:700px){body{padding:18px}main{grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}h1{font-size:32px}b{font-size:15px}}</style><header><h1>A living terminal.</h1><p>Twelve glimpses from Phosphor Arcana. The illustration stays still while refresh bands, gentle flicker, phosphor bloom and persistence animate the glass. Each card carries its own refresh rhythm, phase and glow region. Original code-drawn ASCII light behind curved green phosphor glass.</p><button id="motion" aria-pressed="false">Play the cards</button><p id="state">Static art. No live Slack data or deck state.</p></header><main>"""
        + "".join(tiles)
        + """</main><script>const preference=matchMedia('(prefers-reduced-motion: reduce)');let running=false;function setMotion(on){running=on;document.querySelectorAll('img').forEach(i=>i.src=on?i.dataset.motion:i.dataset.static);document.getElementById('motion').textContent=on?'Still the cards':'Play the cards';document.getElementById('motion').setAttribute('aria-pressed',String(on));document.getElementById('state').textContent=on?'Independent looping scenes. No live Slack data or deck state.':'Static art. No live Slack data or deck state.';}document.getElementById('motion').onclick=()=>setMotion(!running);preference.addEventListener('change',e=>setMotion(!e.matches));setMotion(!preference.matches);</script></html>"""
    )
    path = ROOT / "preview/phosphor-arcana-motion-gallery.html"
    path.write_text(doc)
    print(path)


if __name__ == "__main__":
    main()
