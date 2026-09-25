#!/usr/bin/env python3
"""Build the Celina-to-Halifax 2028 caravan site from data/*.json.

Edit data/stops.json, data/options.json or data/decisions.json, then run:
    python3 build.py
deploy.sh runs this automatically before pushing.
"""
import json, html, datetime as dt
from pathlib import Path

ROOT = Path(__file__).parent
D = lambda f: json.loads((ROOT / "data" / f).read_text())
STOPS, OPTS, DECS, ROUTES = D("stops.json"), D("options.json"), D("decisions.json"), D("routes.json")
LEGS = ROUTES["legs"]
START = dt.date.fromisoformat(OPTS["start"])
TOW_FACTOR = 1.2  # towing takes ~20% longer than OSRM car time
MUST = {"niagara", "pei", "halifax", "acadia"}
SHORT = {"celina": "Rally", "niagara": "Niagara", "thousand": "1000 Is.", "montreal": "Montréal",
         "quebec": "Québec", "edmundston": "", "fundy": "Fundy", "pei": "PEI", "capebreton": "Cape Breton",
         "halifax": "Halifax", "saintjohn": "", "acadia": "Acadia", "whitemtns": "White Mtns",
         "lakegeorge": "", "fingerlakes": "", "erie": ""}
e = html.escape


def fmt(d, year=False):
    return d.strftime("%a %b %-d, %Y" if year else "%a %b %-d")


def plan(key):
    """Expand an option into dated segments with the drive leg into each stop."""
    o = OPTS["options"][key]
    segs, day, prev = [], START, "home"
    for sid, n in o["stops"]:
        leg = LEGS[f"{prev}-{sid}"]
        segs.append(dict(id=sid, nights=n, arrive=day, depart=day + dt.timedelta(n), prev=prev,
                         mi=leg["mi"], tow_h=round(leg["car_h"] * TOW_FACTOR, 1), ferry=leg.get("ferry", False)))
        day += dt.timedelta(n)
        prev = sid
    last = LEGS[f"{prev}-home"]
    home = dict(mi=last["mi"], tow_h=round(last["car_h"] * TOW_FACTOR, 1), date=day, prev=prev)
    nights = sum(s["nights"] for s in segs)
    miles = sum(s["mi"] for s in segs) + home["mi"]
    return dict(key=key, label=o["label"], short=o["short"], note=o["note"], segs=segs, home=home,
                nights=nights, miles=miles, end=day)


PLANS = {k: plan(k) for k in OPTS["options"]}


def page(title, body, depth, head_extra="", scripts=""):
    up = "../" * depth
    nav = [("", "Overview"), ("itinerary/", "Itinerary"), ("route-map/", "Route map"),
           ("campgrounds/", "Campgrounds"), ("decisions/", "Decisions")]
    links = "".join(f'<a href="{up}{p}">{e(t)}</a>' for p, t in nav)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="robots" content="noindex, nofollow">
<title>{e(title)} — Celina to Halifax 2028</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Alegreya:wght@500;700&family=Alegreya+Sans:ital,wght@0,400;0,500;0,700;1,400&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{up}assets/css/site.css">{head_extra}
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>⚓</text></svg>">
</head><body>
<header class="top"><a class="brand" href="{up}">Celina to Halifax <span>2028</span></a><nav>{links}</nav></header>
<main>{body}</main>
<footer>Planning site for Thor &amp; Colleen Thorsen and George &amp; Jenny Volsky. Mileage from OpenStreetMap routing; towing times are estimates (car time + 20%). Campgrounds are candidates until booked.</footer>
{scripts}</body></html>"""


# ---------- signature element: side-by-side trip timeline ----------
def timeline_svg():
    days = max(p["nights"] for p in PLANS.values()) + 1
    W, L, R = 1000, 10, 10
    px = (W - L - R) / days
    rows, y = [], 34
    out = []
    # week gridlines, muted
    for d in range(0, days + 1):
        date = START + dt.timedelta(d)
        if date.weekday() == 6 or d == 0:
            x = L + d * px
            out.append(f'<line x1="{x:.1f}" y1="22" x2="{x:.1f}" y2="{34 + 2 * 78 - 8}" class="tl-grid"/>')
            out.append(f'<text x="{x + 3:.1f}" y="16" class="tl-date">{date.strftime("%b %-d")}</text>')
    for k, p in PLANS.items():
        out.append(f'<text x="{L}" y="{y + 12}" class="tl-row">{e(p["label"])}, {e(p["short"])}: '
                   f'{p["nights"]} nights, home {p["end"].strftime("%b %-d")}, {p["miles"]:,} mi</text>')
        by = y + 20
        for s in p["segs"]:
            d0 = (s["arrive"] - START).days
            x, w = L + d0 * px, s["nights"] * px
            cls = "must" if s["id"] in MUST else ("rally" if s["id"] == "celina" else
                                                   ("transit" if STOPS[s["id"]]["kind"] == "transit" else "stop"))
            name = STOPS[s["id"]]["name"]
            out.append(f'<rect x="{x + 1:.1f}" y="{by}" width="{w - 2:.1f}" height="30" rx="3" class="tl-{cls}">'
                       f'<title>{e(name)}: {fmt(s["arrive"])} to {fmt(s["depart"])}, {s["nights"]} night'
                       f'{"s" if s["nights"] > 1 else ""}</title></rect>')
            lab = SHORT.get(s["id"], "")
            if lab:
                fits = len(lab) * 6.3 < w - 6
                ty = by + 20 if fits else by + 45
                out.append(f'<text x="{x + w / 2:.1f}" y="{ty}" text-anchor="middle" '
                           f'class="tl-lab {"in-" + cls if fits else "out"}">{e(lab)}</text>')
        y += 78
    H = y
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Timeline of both trip options" '
            f'class="timeline">{"".join(out)}</svg>')


def index_page():
    a, b = PLANS["A"], PLANS["B"]
    must = ", ".join(STOPS[m]["name"] for m in ["niagara", "pei", "halifax", "acadia"])
    body = f"""
<section class="hero">
  <p class="dates">June 23 – late July 2028</p>
  <h1>From the Airstream International in Celina to the Halifax waterfront — and home by way of Acadia.</h1>
  <p class="lede">Two Airstreams, four travelers, one loop: out through Ontario and Québec, around the Maritimes, back through Maine and New England. Two versions are on the table.</p>
  <p class="countdown" id="countdown"></p>
</section>
<section class="compare">
  <h2>Both options hit every must-see; Option B adds a week of breathing room</h2>
  <div class="scroll">{timeline_svg()}</div>
  <p class="caption">Each block is one stop, sized by nights. Red blocks are the must-sees ({e(must)}). Unlabeled grey blocks are one-night travel stops. Hover or tap a block for dates.</p>
  <table class="facts">
    <thead><tr><th></th><th>{e(a["label"])}</th><th>{e(b["label"])}</th></tr></thead>
    <tbody>
      <tr><th>Length</th><td>{a["nights"]} nights</td><td>{b["nights"]} nights</td></tr>
      <tr><th>Home</th><td>{fmt(a["end"])}</td><td>{fmt(b["end"])}</td></tr>
      <tr><th>Towing miles</th><td>{a["miles"]:,}</td><td>{b["miles"]:,}</td></tr>
      <tr><th>Stops</th><td>{len(a["segs"])}</td><td>{len(b["segs"])}</td></tr>
      <tr><th>Trade-off</th><td>{e(a["note"])}</td><td>{e(b["note"])}</td></tr>
    </tbody>
  </table>
</section>
<section class="pages">
  <a href="itinerary/"><h3>Itinerary</h3><p>Day-by-day for either option: dates, drives, things to do.</p></a>
  <a href="route-map/"><h3>Route map</h3><p>Real-road route, campground pins, Google Maps and GPS downloads.</p></a>
  <a href="campgrounds/"><h3>Campgrounds</h3><p>Candidates at every stop and the booking tracker.</p></a>
  <a href="decisions/"><h3>Decisions</h3><p>What we still need to settle, and who owns it.</p></a>
</section>"""
    js = f"""<script>
(function(){{var s=new Date("{START.isoformat()}T12:00:00"),n=new Date(),d=Math.round((s-n)/864e5),el=document.getElementById("countdown");
if(d>0)el.textContent=d+" days until we roll into Celina.";else if(d>-40)el.textContent="Day "+(1-d)+" of the trip.";else el.textContent="Trip complete.";}})();
</script>"""
    return page("Overview", body, 0, scripts=js)


def itinerary_page():
    tabs = "".join(f'<button role="tab" data-opt="{k}" aria-selected="{str(k == "A").lower()}">'
                   f'{e(p["label"])}, {e(p["short"])}</button>' for k, p in PLANS.items())
    panes = []
    for k, p in PLANS.items():
        items = []
        for i, s in enumerate(p["segs"], 1):
            st = STOPS[s["id"]]
            frm = STOPS[s["prev"]]["name"] if s["prev"] != "home" else "home"
            drive = (f'{s["mi"]} mi from {e(frm)}, about {s["tow_h"]} h towing'
                     + (" plus the Wood Islands–Caribou ferry (about 75 min crossing)" if s["ferry"] else ""))
            acts = "".join(f"<li>{e(x)}</li>" for x in st["activities"])
            camps = "; ".join(e(c["name"]) for c in st["campgrounds"]) or "Not chosen yet"
            items.append(f"""<li class="stop k-{st['kind']}{' must' if s['id'] in MUST else ''}">
<div class="when"><span class="n">{i}</span><b>{s['arrive'].strftime('%b %-d')}–{s['depart'].strftime('%b %-d')}</b><span>{s['nights']} night{'s' if s['nights'] > 1 else ''}</span></div>
<div class="what"><h3>{e(st['name'])} <small>{e(st['place'])}</small></h3>
<p class="drive">{drive}</p>{f"<p>{e(st['blurb'])}</p>" if st['blurb'] else ''}
{f'<ul>{acts}</ul>' if acts else ''}<p class="camp">Campground: {camps}</p></div></li>""")
        h = p["home"]
        items.append(f"""<li class="stop k-home"><div class="when"><span class="n">⌂</span><b>{h['date'].strftime('%b %-d')}</b><span>home</span></div>
<div class="what"><h3>Home</h3><p class="drive">{h['mi']} mi from {e(STOPS[h['prev']]['name'])}, about {h['tow_h']} h towing</p></div></li>""")
        panes.append(f'<section class="pane" data-opt="{k}"{"" if k == "A" else " hidden"}>'
                     f'<p class="lede">{e(p["note"])} {p["nights"]} nights, {p["miles"]:,} towing miles, home {fmt(p["end"], True)}.</p>'
                     f'<ol class="stops">{"".join(items)}</ol></section>')
    body = f'<h1>Itinerary</h1><div class="tabs" role="tablist">{tabs}</div>{"".join(panes)}'
    js = """<script>
document.querySelectorAll('[role=tab]').forEach(function(b){b.addEventListener('click',function(){
var o=b.dataset.opt;document.querySelectorAll('[role=tab]').forEach(function(x){x.setAttribute('aria-selected',x===b)});
document.querySelectorAll('.pane').forEach(function(p){p.hidden=p.dataset.opt!==o});try{localStorage.setItem('opt',o)}catch(e){}})});
try{var s=localStorage.getItem('opt');if(s)document.querySelector('[role=tab][data-opt="'+s+'"]').click()}catch(e){}
</script>"""
    return page("Itinerary", body, 1, scripts=js)


def option_line(k):
    p = PLANS[k]
    pts = []
    for s in p["segs"] + [dict(id="home", prev=p["home"]["prev"])]:
        key = f'{s["prev"]}-{s["id"]}'
        pts += LEGS[key]["geom"]
    return pts


def route_page():
    data = {k: {"line": option_line(k), "stops": [
        dict(id=s["id"], name=STOPS[s["id"]]["name"], place=STOPS[s["id"]]["place"],
             dates=f'{s["arrive"].strftime("%b %-d")}–{s["depart"].strftime("%b %-d")}',
             nights=s["nights"], must=s["id"] in MUST, kind=STOPS[s["id"]]["kind"],
             camps=[dict(name=c["name"], lat=c["lat"], lon=c["lon"]) for c in STOPS[s["id"]]["campgrounds"]],
             lat=STOPS[s["id"]]["lat"], lon=STOPS[s["id"]]["lon"]) for s in p["segs"]]}
            for k, p in PLANS.items()}
    tabs = "".join(f'<button role="tab" data-opt="{k}" aria-selected="{str(k == "A").lower()}">'
                   f'{e(p["label"])}, {e(p["short"])}</button>' for k, p in PLANS.items())
    dl = " ".join(f'<a href="caravan-2028-option-{k.lower()}.kml" download>Option {k} KML</a> '
                  f'<a href="caravan-2028-option-{k.lower()}.gpx" download>Option {k} GPX</a>' for k in PLANS)
    body = f"""<h1>Route map</h1><div class="tabs" role="tablist">{tabs}</div>
<div id="map" aria-label="Route map"></div>
<p class="caption">Red pins are must-see stops; small dots are campground candidates. The dashed segment is the PEI–Nova Scotia ferry.</p>
<p class="downloads">Downloads: {dl}</p>
<p class="caption">KML imports into Google My Maps (Create map → Import). GPX loads into most RV GPS units and apps.</p>"""
    head = ('\n<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">')
    js = f"""<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
<script>
var DATA={json.dumps(data, ensure_ascii=False)};
var map=L.map('map',{{scrollWheelZoom:false}});
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png',{{maxZoom:18,attribution:'&copy; OpenStreetMap &copy; CARTO'}}).addTo(map);
var layer=L.layerGroup().addTo(map);
function draw(o){{layer.clearLayers();var d=DATA[o];
L.polyline(d.line,{{color:'#2E5266',weight:4,opacity:.85}}).addTo(layer);
d.stops.forEach(function(s,i){{
 s.camps.forEach(function(c){{L.circleMarker([c.lat,c.lon],{{radius:4,color:'#2E5266',weight:1,fillColor:'#fff',fillOpacity:1}}).bindTooltip(c.name).addTo(layer)}});
 L.circleMarker([s.lat,s.lon],{{radius:s.kind==='transit'?5:8,color:'#fff',weight:2,fillColor:s.must?'#C23B2E':(s.kind==='transit'?'#8A9BA4':'#2E5266'),fillOpacity:1}})
 .bindPopup('<b>'+(i+1)+'. '+s.name+'</b><br>'+s.place+'<br>'+s.dates+' ('+s.nights+' night'+(s.nights>1?'s':'')+')<br><small>'+s.camps.map(function(c){{return c.name}}).join('<br>')+'</small>').addTo(layer);}});
L.polyline([[45.9536,-62.7461],[45.7414,-62.6798]],{{color:'#C23B2E',weight:3,dashArray:'6 6'}}).bindTooltip('Wood Islands–Caribou ferry').addTo(layer);
map.fitBounds(L.polyline(d.line).getBounds(),{{padding:[20,20]}});}}
document.querySelectorAll('[role=tab]').forEach(function(b){{b.addEventListener('click',function(){{
document.querySelectorAll('[role=tab]').forEach(function(x){{x.setAttribute('aria-selected',x===b)}});draw(b.dataset.opt);try{{localStorage.setItem('opt',b.dataset.opt)}}catch(e){{}}}})}});
var st='A';try{{st=localStorage.getItem('opt')||'A'}}catch(e){{}}document.querySelector('[role=tab][data-opt="'+st+'"]').click();
</script>"""
    return page("Route map", body, 1, head_extra=head, scripts=js)


def kml(k):
    p = PLANS[k]
    coords = " ".join(f"{lon},{lat},0" for lat, lon in option_line(k))
    marks = []
    for i, s in enumerate(p["segs"], 1):
        for c in STOPS[s["id"]]["campgrounds"]:
            marks.append(f'<Placemark><name>{i}. {e(STOPS[s["id"]]["name"])} — {e(c["name"])}</name>'
                         f'<description>{fmt(s["arrive"])} to {fmt(s["depart"])}, {s["nights"]} night(s). Candidate campground.</description>'
                         f'<Point><coordinates>{c["lon"]},{c["lat"]},0</coordinates></Point></Placemark>')
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document><name>Celina to Halifax 2028 — {e(p['label'])} ({e(p['short'])})</name>
<Style id="r"><LineStyle><color>ff66522e</color><width>4</width></LineStyle></Style>
<Placemark><name>Route</name><styleUrl>#r</styleUrl><LineString><tessellate>1</tessellate><coordinates>{coords}</coordinates></LineString></Placemark>
{''.join(marks)}</Document></kml>"""


def gpx(k):
    p = PLANS[k]
    wpts = []
    for i, s in enumerate(p["segs"], 1):
        for c in STOPS[s["id"]]["campgrounds"][:1]:
            wpts.append(f'<wpt lat="{c["lat"]}" lon="{c["lon"]}"><name>{i}. {e(c["name"])}</name>'
                        f'<desc>{e(STOPS[s["id"]]["name"])}, {fmt(s["arrive"])} for {s["nights"]} night(s)</desc></wpt>')
    trk = "".join(f'<trkpt lat="{lat}" lon="{lon}"/>' for lat, lon in option_line(k))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="halifax-caravan-2028" xmlns="http://www.topografix.com/GPX/1/1">
{''.join(wpts)}<trk><name>Celina to Halifax 2028 — {e(p['label'])}</name><trkseg>{trk}</trkseg></trk></gpx>"""


def campgrounds_page():
    rows = []
    inA = {s["id"] for s in PLANS["A"]["segs"]}
    inB = {s["id"] for s in PLANS["B"]["segs"]}
    seen = []
    for s in PLANS["B"]["segs"]:
        if s["id"] in seen:
            continue
        seen.append(s["id"])
        st = STOPS[s["id"]]
        opts = " & ".join(x for x, S in (("A", inA), ("B", inB)) if s["id"] in S)
        camps = st["campgrounds"] or [dict(name="Not chosen yet", type="", notes="")]
        for j, c in enumerate(camps):
            first = j == 0
            rows.append(f"""<tr{' class="grp"' if first else ''}>
<th scope="row">{e(st['name']) if first else ''}{f'<small>Option {opts}</small>' if first else ''}</th>
<td>{e(c['name'])}</td><td>{e(c.get('type', ''))}</td><td>{e(c.get('notes', ''))}</td>
<td class="todo">Check</td><td class="todo">Check</td><td>Candidate</td></tr>""")
    body = f"""<h1>Campgrounds</h1>
<p class="lede">Every stop has at least one candidate. None are booked. Next pass checks each one for our rigs and records when 2028 reservations open. Thor &amp; Colleen's rig: 46 ft combined, 24 ft trailer, 30 A. Volskys' rig: to be added.</p>
<div class="scroll"><table class="camps"><thead><tr><th>Stop</th><th>Campground</th><th>Type</th><th>Notes</th><th>Fits both rigs</th><th>Booking opens</th><th>Status</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""
    return page("Campgrounds", body, 1)


def decisions_page():
    items = "".join(f"""<li class="{d['status']}"><h3>{e(d['q'])}</h3><p class="who">{e(d['who'])}, {e(d['status'])}</p>
{f"<p>{e(d['note'])}</p>" if d['note'] else ''}</li>""" for d in DECS)
    body = f'<h1>Decisions</h1><p class="lede">Open questions and who owns each one.</p><ul class="decisions">{items}</ul>'
    return page("Decisions", body, 1)


def write(rel, text):
    f = ROOT / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)


if __name__ == "__main__":
    write("index.html", index_page())
    write("itinerary/index.html", itinerary_page())
    write("route-map/index.html", route_page())
    write("campgrounds/index.html", campgrounds_page())
    write("decisions/index.html", decisions_page())
    for k in PLANS:
        write(f"route-map/caravan-2028-option-{k.lower()}.kml", kml(k))
        write(f"route-map/caravan-2028-option-{k.lower()}.gpx", gpx(k))
    for k, p in PLANS.items():
        print(f"Option {k}: {p['nights']} nights, {p['miles']:,} mi, home {p['end']}")
