# Route Finder

Upload a GPX file from a race or training route, and find similar road-running routes near a location — matched by distance, elevation gain and the shape of climbs/descents (not just total distance).

Useful for training on terrain similar to an upcoming race,if you can't run the actual race course beforehand.

## Status
Currently a Python script, no UI yet.

## Setup
1. Clone this repo
2. Create a virtual environment: `python -m venv .venv`
3. Activate it:
   - Windows: `.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Get a free Google Cloud API key with Routes API and Elevation API enabled, 
   and add it to a `.env` file in the project root:
   GOOGLE_MAPS_API_KEY=your_key_here
6. Run it: `python main.py your_route.gpx`

## What it does
- Parses your uploaded GPX into a distance/elevation profile
- Detects climb and downhill segments (e.g. "3% climb from km 7.8–9.1")
- Generates test routes near a given location using Google Maps
- Ranks routes by how closely their elevation shape matches your uploaded route
- Outputs a Google Maps link and a GPX file