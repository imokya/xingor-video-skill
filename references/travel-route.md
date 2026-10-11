# travel-route · 旅行路线

A **trip animation from one city to a place in another**: a globe with a curved flight line that the camera follows, a
seamless zoom into a drawn vector map, the map folding into a glass card with a frosted boarding pass, a dive through
the pass onto the runway, a short 3D flight over the drawn map, a short taxi drive on real roads and a pin at the
destination. 16:9 1920×1080 60 fps by default, about 16 s. First made for 上海浦东 → 哈尔滨太平 → 斯大林公园, modelled
frame by frame on a reference the user liked (`~/Desktop/xingor-video-skill/sample.mp4` 0:24–0:36).

Everything lives in `scripts/travel/` and runs with the work-dir venv (numpy, pillow, skia, imageio-ffmpeg).

| file | does |
|---|---|
| `trip_example.json` | the trip config: origin / dest city + airport (name, IATA code, lon/lat, dest terminal), poi (name, sub line, lon/lat, optional `route_end`), ticket, size, fps, optional `timing` overrides, `taxi_tail_km` |
| `travel_prep.py` | downloads and caches base data, then fetches this trip's OSM + OSRM data into `./data/` |
| `travel_core.py` | `Trip(trip.json)`: Mercator ground, map layers, place / road names, runway choice, flight + taxi tracks, the whole camera choreography and per-frame plane / car / card states; `export_web()` |
| `travel_models.py` | low-poly airliner and taxi meshes |
| `travel_render.py` | `Renderer(trip)`: skia drawing identical to the web player → `still()` / `render()` mp4 |
| `player/` | the browser preview (WebGL globe, canvas map, CSS 3D boarding pass), play / pause / scrub / speed |
| `travel.py` | CLI: `prep`, `web [--serve 8765]`, `stills`, `render` |

## Workflow
1. **Trip config** — copy `trip_example.json` to the project as `trip.json`, fill in the cities, airports (lon/lat near
   the runways), the destination terminal (taxi start), the poi and the ticket. If the user has no real flight, use
   clearly fake data (`"demo": true` prints `· 示意航班`; never a real airline's flight number).
2. **Data** — ask before downloading (name sources and sizes), then `python travel.py prep trip.json`.
   - Cached once in `~/.cache/xingor-travel/` (public domain): Natural Earth 10m land / coast / rivers / lakes / roads /
     populated places (with `NAME_ZH`) / urban areas (~35 MB of zips), NASA Blue Marble, clouds, Black Marble (~4 MB).
   - Per trip (`./data/`): Overpass for the origin airport area, the dest airport + approach + city up to the poi
     (minor roads and buildings only near the poi), place names; OSRM driving route terminal → poi. Overpass often
     returns 504 — the script retries and alternates mirrors.
3. **Preview in the browser** — `python travel.py web trip.json --serve 8765` (or add a `.claude/launch.json` entry
   and `preview_start`). `?t=9.6` jumps to a time, `&play` autoplays. **Iterate here** — a change is a re-export
   (seconds), not a re-render (minutes). Check by pausing at the busy moments with `javascript_tool`
   (`playing=false; cur=8.2`) and zoomed screenshots.
4. **Stills / render** — `python travel.py stills trip.json 2.4 6.5 8.4 10 13.4 15.6`, then
   `python travel.py render trip.json 成片.mp4` (≈ 2–3 min for 16 s at 60 fps on an M1; run in the background).

## Choreography (what the user approved, in order — keep it)
| time | beat | how |
|---|---|---|
| 0–1 s | **globe full view holds** | WebGL / numpy orthographic globe: Blue Marble + clouds + night lights on the dark side + ocean glint + rim scattering, sun placed so both cities are on the day side |
| 1–3.1 s | push in on the origin; the flight line draws origin → dest and **the camera follows the line head** | the line is a **curved arc** (spherical quadratic curve bowed east, `arc_point`, plus a little height) — a plain great circle looks straight from above |
| 3.1–4.7 s | pull back to see the whole line, then zoom into the origin airport | globe radius and the vector map's px/km are matched at the hand-over (`D_XFADE`); 0.35 s cross-fade |
| 4.7–5.7 s | the drawn map keeps zooming; outside the card it fades to a light background while the card's glass edge appears | "the map folds into a card" — no phone body, no status bar, no title text |
| 5.7–7.2 s | the card's top tilts back (**bottom edge nearer**, wide bottom), a frosted boarding pass fades in out of a blur, slow push | wide lens (F 900) for strong perspective |
| 7.2–8.4 s | accelerate into the pass: text grows huge and blurs, pass through, decelerate onto the runway with the plane | pitch only increases (≈38° → 46° → 60°); never flips sign mid-move |
| 8–12 s | **flight 4 s**: roll, climb, cruise (camera rises to ~700 km), descent, landing | path = straight climb-out along the runway, one cubic Hermite arc, straight final along the landing runway; the longest runway is chosen and oriented toward / from the other city |
| 12–14.5 s | quick camera move into the city; **the taxi drives only the last ~3 km in 2 s** | the earlier part of the route is drawn as already driven; the info card still shows the full OSRM km / minutes |
| 14.5 s– | pin drops with ripples at the poi; big name left of the pin | other labels keep out of the title's box |

## Map style
- Everything after the globe is **drawn vector map** (Amap-like): Natural Earth land / coast / rivers / lakes / urban
  areas / major roads at country scale, OSM roads (width by class and by distance to the camera), water, parks,
  runways / taxiways / aprons, rail, buildings near the poi. Never switch to satellite imagery mid-flight (the user
  rejected it: "要保持绘制地图").
- **No national or provincial borders**, ever: publishing a map with borders in China needs the standard map and a
  审图号. Land / sea / rivers / roads / cities only.
- **Names**: cities by Natural Earth rank (shown by camera distance), OSM districts / towns / streets / attractions
  closer in, road names laid **along the road** glyph by glyph, upright, skipped where the road bends > 50°.
  Labels fade in / out and never overlap; Cyrillic duplicates are dropped.
- Credits bottom right: `地图数据 © OpenStreetMap 贡献者 · Natural Earth` (flight) / `… · 路线 OSRM` (taxi).

## Motion rules learned the hard way
- **No sudden turns.** The flight path is one smooth arc (max yaw ≈ 45°/s); heading and bank are Gaussian-smoothed
  per frame; bank follows the smoothed turn rate.
- **The taxi's nose must follow the road**: round the OSRM corners (radius 0.2 km) and use the tangent of that
  rounded path — never time-smooth the heading (it lags and the car drives sideways).
- **Taxi speed like a real car**: per-point speed limit from curvature (yaw ≤ 170°/s), forward + backward passes
  limiting acceleration (brake before a corner, accelerate out), slow start and stop; solve the top speed so the
  segment fits its duration. Speed jumps read as stutter at corners.
- **The map should not spin with the car**: the taxi camera heading follows only the 6 km trend (≈ 36°/s max);
  the car turns, the world stays calm.
- Cameras are precomputed per frame and Gaussian-smoothed after the dive; everything before it is analytic.
- Keep positions / sizes / angles as floats (sub-pixel), motion blur only on the dive.
- Short beats: the user twice asked for shorter flight / taxi; 4 s + 2 s matches the reference.

## Reporting
Say which data is real (distances: great-circle airport ↔ airport, OSRM route km / minutes; runways, roads and names
from OSM) and which is invented (ticket number and times when `demo`). Mention the credits line, the absence of
borders, and that OSM names can be outdated. Offer the web preview link for review before the final render.
