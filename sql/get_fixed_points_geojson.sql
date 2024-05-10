-- Get fixed points and convert to GeoJSON
-- The Supabase JS client will call this as a Remote Function Call
CREATE OR REPLACE FUNCTION get_puntos_fijos_geojson() returns TABLE (geojson json) as $$
BEGIN
  RETURN QUERY
  SELECT json_build_object(
    'type', 'FeatureCollection',
    'features', json_agg(ST_AsGeoJSON(pf.*)::json)
  ) AS geojson
  FROM puntos_fijos pf;
END
$$ LANGUAGE plpgsql ;