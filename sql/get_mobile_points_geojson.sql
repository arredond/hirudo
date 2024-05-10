-- Filter mobile points for a specific date and convert to GeoJSON
-- The Supabase JS client will call this as a Remote Function Call
CREATE FUNCTION get_puntos_moviles_geojson(filter_date TEXT) returns TABLE (geojson json) as $$
BEGIN
  RETURN QUERY
  SELECT json_build_object(
    'type', 'FeatureCollection',
    'features', json_agg(ST_AsGeoJSON(pm.*)::json)
  ) AS geojson
  FROM puntos_moviles pm
  WHERE pm.fecha = filter_date;
END
$$ LANGUAGE plpgsql ;