# District boundaries in CSV format

- `india_districts.csv`: 676 districts, all 13 original GADM property fields,
  `GEOMETRY_TYPE`, `CENTROID_X`, `CENTROID_Y` and `VERTEX_COUNT`.
- `boundary_coordinates.csv`: 275,432 vertices. Join to districts by `GID_2`.
  `POLYGON_INDEX`, `RING_INDEX` and `VERTEX_INDEX` are zero-based and preserve
  geometry order. Each vertex has longitude and latitude in degrees.

For MultiPolygon, group vertices by polygon then ring. For Polygon, polygon
index is zero. Ring zero is the exterior; subsequent rings are holes.

Representative coordinates average all source vertices, including closing
vertices and holes, exactly as the original builder did. These are not
area-weighted geographic centroids. The merge reads `india_districts.csv`;
the complete coordinate table is preserved for maps and source auditing.

All source properties and ordered coordinates were checked by reading back the
CSVs before removing the ZIP. Rebuilding the master from these CSVs produced
byte-identical results: 2,018 rows and 30 columns.

Source: GADM 4.1, administrative level 2, India.
https://gadm.org/data.html
License: https://gadm.org/license.html
