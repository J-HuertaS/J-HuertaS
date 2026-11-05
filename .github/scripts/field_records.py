#!/usr/bin/env python3
"""PLATE 04 — FIELD RECORDS for the J-HuertaS profile README.

Runs in GitHub Actions (stdlib only). Reads the owner's public activity from the
GitHub GraphQL API and draws it in the Juan Huertas brand: the contribution
calendar is the sheet's own dot grid, inked by activity; the busiest days take
the hanko red. Writes assets/records-light.svg and assets/records-dark.svg.

  GITHUB_TOKEN=... python3 .github/scripts/field_records.py
  python3 .github/scripts/field_records.py --sample   # local layout check, fake data
"""
import base64, datetime as dt, json, os, random, sys, urllib.request

LOGIN = os.environ.get("RECORDS_LOGIN", "J-HuertaS")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
KIT = os.path.join(ROOT, ".github", "brand")
OUT = os.path.join(ROOT, "assets")

THEMES = {
    "light": dict(paper="#ffffff", ink="#141414", muted="#555555", hair="#d6d2c8", hanko="#b8312f", lvl=["#d6d2c8", "#9a958b", "#5f5b54", "#2f2c28", "#141414"]),
    "dark": dict(paper="#141414", ink="#f2efe8", muted="#a8a29a", hair="#34312d", hanko="#c9433f", lvl=["#34312d", "#6b665e", "#a8a29a", "#d4cfc5", "#f2efe8"]),
}

QUERY = """query($login:String!){user(login:$login){createdAt
 repositories(ownerAffiliations:OWNER,isFork:false,privacy:PUBLIC,first:100){totalCount nodes{name languages(first:8,orderBy:{field:SIZE,direction:DESC}){edges{size node{name}}}}}
 contributionsCollection{totalCommitContributions totalPullRequestContributions restrictedContributionsCount
  contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}"""

def fetch():
    token = os.environ["GITHUB_TOKEN"]
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": QUERY, "variables": {"login": LOGIN}}).encode(),
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                                          "User-Agent": "field-records"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL error: {data['errors']}")
    return data["data"]["user"]

def sample():
    rnd = random.Random(7)
    start = dt.date.today() - dt.timedelta(days=dt.date.today().weekday() + 1 + 52 * 7)
    weeks = []
    for w in range(53):
        days = []
        for d in range(7):
            day = start + dt.timedelta(days=w * 7 + d)
            if day > dt.date.today(): break
            busy = 0.35 + 0.5 * (w > 30)
            c = 0 if rnd.random() > busy else int(rnd.expovariate(1 / 4)) + 1
            days.append({"date": day.isoformat(), "contributionCount": c})
        weeks.append({"contributionDays": days})
    langs = [("TypeScript", 52), ("Python", 21), ("C++", 12), ("JavaScript", 8), ("CSS", 4)]
    return {"createdAt": "2023-02-01T00:00:00Z",
            "repositories": {"totalCount": 14, "nodes": [{"name": "x", "languages": {"edges": [{"size": s * 1000, "node": {"name": n}} for n, s in langs]}}]},
            "contributionsCollection": {"totalCommitContributions": 0, "totalPullRequestContributions": 0, "restrictedContributionsCount": 0,
                                        "contributionCalendar": {"totalContributions": sum(d["contributionCount"] for w in weeks for d in w["contributionDays"]), "weeks": weeks}}}

def streaks(days):
    longest = cur = 0
    for d in days:
        cur = cur + 1 if d["contributionCount"] else 0
        longest = max(longest, cur)
    # current streak counts back from today (today may still be empty)
    now = 0
    for i, d in enumerate(reversed(days)):
        if d["contributionCount"]: now += 1
        elif i == 0: continue
        else: break
    return longest, now

def b64(name):
    with open(os.path.join(KIT, "fonts", name), "rb") as f:
        return base64.b64encode(f.read()).decode()

def esc(s): return s.replace("&", "&amp;").replace("<", "&lt;")

def render(u, theme, t):
    W, H = 1000, 744
    S = "font-family:'IS','Instrument Serif',Georgia,serif"
    M = "font-family:'JB','JetBrains Mono',Menlo,monospace"
    J = "font-family:'ZA','Zen Antique',serif"
    o = []
    def txt(x, y, s, size, fam=M, fill=None, anchor="start", extra=""):
        o.append(f'<text x="{x}" y="{y}" text-anchor="{anchor}" style="{fam};font-size:{size}px" fill="{fill or t["ink"]}" {extra}>{s}</text>')

    cc = u["contributionsCollection"]; cal = cc["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    total = cal["totalContributions"]
    active = sum(1 for d in days if d["contributionCount"])
    longest, current = streaks(days)

    # ---- header
    o.append(f'<line x1="48" y1="0" x2="{W-48}" y2="0" stroke="{t["ink"]}" stroke-width="2"/>')
    txt(48, 40, "PLATE 04 — FIELD RECORDS", 11, M, t["muted"], extra='letter-spacing="3"')
    txt(W - 48, 40, f"updated {dt.date.today().isoformat()}", 11, M, t["muted"], "end", 'letter-spacing="1"')
    txt(44, 118, "Field records,", 72, S)

    # ---- three readings
    readings = [(f"{total:,}", "contributions", "last 12 months"),
                (f"{active}", "days in the field", f"of {len(days)}"),
                (f"{longest}", "longest streak", f"current: {current} day{'s' if current != 1 else ''}")]
    for i, (num, lab, sub) in enumerate(readings):
        x = 48 + i * 308
        o.append(f'<line x1="{x}" y1="252" x2="{x+272}" y2="252" stroke="{t["hair"]}" stroke-width="1"/>')
        txt(x, 238, num, 56, S, t["hanko"] if i == 2 else t["ink"])
        txt(x, 276, lab, 13, M)
        txt(x, 296, esc(sub), 11, M, t["muted"])

    # ---- calendar: one dot per day, 53 weeks × 7 days at a 16px pitch
    gx, gy, p = 48 + 6, 384, 16
    counts = sorted(d["contributionCount"] for d in days if d["contributionCount"])
    def q(f): return counts[min(len(counts) - 1, int(f * len(counts)))] if counts else 1
    th = [q(.25), q(.5), q(.75), q(.97)]
    month_seen = set()
    for wi, w in enumerate(cal["weeks"]):
        for d in w["contributionDays"]:
            date = dt.date.fromisoformat(d["date"]); di = (date.weekday() + 1) % 7
            c = d["contributionCount"]
            x, y = gx + wi * p, gy + di * p
            if c == 0:
                o.append(f'<circle cx="{x}" cy="{y}" r="1.4" fill="{t["lvl"][0]}"/>')
            else:
                lvl = 1 + sum(c > v for v in th[:3])
                top = c >= th[3] and c > 1
                r = [0, 2.6, 3.6, 4.6, 5.6][lvl]
                o.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{t["hanko"] if top else t["lvl"][lvl]}"><title>{d["date"]}: {c}</title></circle>')
            if date.day <= 7 and di == 0 and (date.year, date.month) not in month_seen:
                month_seen.add((date.year, date.month))
                txt(x - 4, gy - 22, date.strftime("%b").lower(), 10, M, t["muted"])
    # legend
    ly = gy + 7 * p + 18
    txt(gx - 6, ly + 4, "less", 10, M, t["muted"])
    for i, r in enumerate([1.4, 2.6, 3.6, 4.6, 5.6]):
        o.append(f'<circle cx="{gx + 40 + i * 16}" cy="{ly}" r="{r}" fill="{t["lvl"][i]}"/>')
    txt(gx + 128, ly + 4, "more", 10, M, t["muted"])
    o.append(f'<circle cx="{gx + 186}" cy="{ly}" r="5.6" fill="{t["hanko"]}"/>')
    txt(gx + 198, ly + 4, "busiest days", 10, M, t["muted"])
    txt(W - 48, ly + 4, "fig. d — one dot per day, inked by activity", 10.5, M, t["muted"], "end")

    # ---- languages as soil strata
    langs = {}
    for r in u["repositories"]["nodes"]:
        for e in r["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]
    tot = sum(langs.values()) or 1
    top = sorted(langs.items(), key=lambda kv: -kv[1])[:5]
    sy = ly + 62
    txt(48, sy, f"languages in the soil · {u['repositories']['totalCount']} public repositories", 11, M, t["muted"], extra='letter-spacing="1"')
    x = 48; barw = W - 96
    fills = [t["ink"], t["lvl"][3], t["lvl"][2], t["lvl"][1], t["lvl"][0]]
    for i, (name, size) in enumerate(top):
        w = barw * size / tot
        o.append(f'<rect x="{x:.1f}" y="{sy + 16}" width="{max(w - 3, 1):.1f}" height="10" fill="{fills[i]}"/>')
        if w > 70:
            txt(x, sy + 46, esc(name), 12, M)
            txt(x, sy + 62, f"{100 * size / tot:.0f}%", 11, M, t["muted"])
        x += w
    # ---- colophon
    cy = sy + 112
    o.append(f'<line x1="48" y1="{cy}" x2="{W-48}" y2="{cy}" stroke="{t["ink"]}" stroke-width="1"/>')
    txt(48, cy + 62, "Juan Huertas", 40, S)
    txt(48, cy + 92, "I grow software.", 12, M, t["muted"])
    txt(W - 140, cy + 62, f'<tspan style="{J};font-size:22px">育てる</tspan>', 22, M, t["ink"], "end")
    txt(W - 140, cy + 86, "sodateru — to grow, to raise", 11, M, t["muted"], "end")
    with open(os.path.join(KIT, "hatake.svg")) as f:
        seal = f.read().replace("#B8312F", t["hanko"])
    vb = seal.split('viewBox="')[1].split('"')[0]
    body = seal[seal.index(">") + 1: seal.rindex("</svg>")].replace('id="edge"', 'id="hk-edge"').replace("url(#edge)", "url(#hk-edge)") \
        .replace('id="carve"', 'id="hk-carve"').replace("url(#carve)", "url(#hk-carve)")
    sx, sy2, ss = W - 124, cy + 22, 76
    o.append(f'<g transform="rotate(-3 {sx+ss/2} {sy2+ss/2})"><svg x="{sx}" y="{sy2}" width="{ss}" height="{ss}" viewBox="{vb}">{body}</svg></g>')
    H = cy + 140

    css = (f"@font-face{{font-family:'IS';src:url(data:font/woff2;base64,{b64('instrument-serif.woff2')}) format('woff2')}}"
           f"@font-face{{font-family:'JB';src:url(data:font/woff2;base64,{b64('jetbrains-mono.woff2')}) format('woff2')}}"
           f"@font-face{{font-family:'ZA';src:url(data:font/woff2;base64,{b64('zen-antique-sodateru.woff2')}) format('woff2')}}")
    defs = f'<defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><circle cx="12" cy="12" r="1" fill="{t["hair"]}"/></pattern></defs>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
            f'aria-label="Field records: {total} contributions in the last 12 months, {active} active days, longest streak {longest} days.">'
            f'<title>Field records — {total} contributions in the last 12 months</title><style>{css}</style>{defs}'
            f'<rect width="{W}" height="{H}" fill="{t["paper"]}"/><rect width="{W}" height="{H}" fill="url(#grid)"/>'
            + "".join(o) + "</svg>")

if __name__ == "__main__":
    u = sample() if "--sample" in sys.argv else fetch()
    out = sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else OUT
    os.makedirs(out, exist_ok=True)
    for name, t in THEMES.items():
        with open(os.path.join(out, f"records-{name}.svg"), "w") as f:
            f.write(render(u, name, t))
    print("field records written")
