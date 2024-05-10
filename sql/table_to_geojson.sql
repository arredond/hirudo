-- DEPRECATED: create a GeoJSON view of a table
DROP VIEW IF EXISTS {t}_geojson;
CREATE OR REPLACE VIEW {t}_geojson AS (
	SELECT
	json_build_object(
		'type', 'FeatureCollection',
		'features', json_agg(ST_AsGeoJSON(t.*)::json)
	) AS geojson
	FROM {t} t
);
