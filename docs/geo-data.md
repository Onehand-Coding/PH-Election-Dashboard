# Boundary Data

The dashboard bundles two GeoJSON files in
`src/ph_election_dashboard/geo_data/`:

- `ph_regions.geojson`: 18 regions, from
  `https://raw.githubusercontent.com/faeldon/philippines-json-maps/master/latest/geojson/country/lowres/country.0.001.json`
- `ph_island_groups.geojson`: 3 island groups, from
  `https://raw.githubusercontent.com/faeldon/philippines-json-maps/master/latest/geojson/islandgroups/lowres/islandgroups.0.001.json`

Retrieved: 2026-11-01.

The GeoJSON was prepared by `faeldon/philippines-json-maps` (MIT). The
underlying boundaries come from the Philippine Statistics Authority (PSA) and
the National Mapping and Resource Information Authority (NAMRIA), distributed
through OCHA's Philippines administrative boundaries (COD-AB), licensed
CC BY-IGO.

If you republish the map, credit PSA and NAMRIA through OCHA's COD-AB. The app
displays this attribution below every map.
