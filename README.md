# Celina to Halifax 2028

Planning site for the 2028 Airstream caravan — Thor & Colleen Thorsen with George & Jenny Volsky. Starts at the 71st ACI International Rally (Mercer County Fairgrounds, Celina OH, June 24–29, 2028), loops through Ontario and Québec to the Maritimes, and returns through Maine and New England.

Two options side by side:
- **Option A — 5 weeks:** 34 nights, home about July 27
- **Option B — 6 weeks:** 39 nights, home about August 1

Must-sees in both: Niagara Falls (Canadian side), Prince Edward Island, Halifax, Acadia NP.

## Editing
All content lives in `data/`:
- `stops.json` — places, activities, campground candidates
- `options.json` — stop order and nights for each option
- `decisions.json` — open questions
- `routes.json` — road geometry and mileage (OpenStreetMap / OSRM)

Then run `./deploy.sh "message"` — it rebuilds and pushes. `python3 build.py` alone rebuilds locally.

## Pages
Overview (timeline comparing both options), Itinerary, Route map (with KML/GPX downloads), Campgrounds, Decisions.

Not indexed by search engines (`robots.txt` + `noindex`); share the link directly.
