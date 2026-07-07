# SusBiome Next.js Frontend

Premium Next.js frontend for the SusBiome Northeast India district outlook.

This site is intentionally scoped to the production-ready public surface:

- Northeast India state and district selection
- 15, 30, 60, and 90 day planning outlooks
- Flood, drought, and cyclone only
- District boundary map from local geospatial artifacts
- Source attribution and public disclaimer

The local frontend reads bundled public data from:

- `frontend/public/data/susbiome-outlook.json`
- `frontend/public/data/ne-district-boundaries.geojson`

Regenerate those files from current serving artifacts with:

```bash
python -m scripts.frontend.build_static_payload
```

Local development:

```bash
cd frontend
npm install
npm run dev
```

Render deployment:

- Frontend service: Node / Next.js
- Backend service: Docker / FastAPI
- Blueprint: `render.yaml`

Set `NEXT_PUBLIC_SUSBIOME_API_BASE` for production API-backed requests. When it
is empty, the console uses the bundled `/data/*.json` files so local previews
still work without the backend running.

- `/api/outlook`
- `/api/outlook/boundaries`
