import { createClient } from 'https://cdn.skypack.dev/@supabase/supabase-js';

// Fetch data! This is the public API key so it only has read permissions
const SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlhdCI6MTYzMzEyNDA0MywiZXhwIjoxOTQ4NzAwMDQzfQ.G3LHvzBbeMhZp9LktL9WcIOPv2Bb9vhQe2CnieQBMEI';
const SUPABASE_URL = "https://rniahokoaxvcljohlabg.supabase.co";

// Create a single supabase client for interacting with your database
const supabase = createClient(SUPABASE_URL, SUPABASE_KEY)

// Wrapper function to fetch geojson data from Supabase
async function fetchKeys(table) {
    const { data, error } = await supabase
        .from(table)
        .select()
        return data
}

async function fetchFixedPointsGeoJSON() {
    const { data, error } = await supabase
        .from(`puntos_fijos_geojson`)
        .select('geojson')
        return data[0]['geojson']
}

async function fetchMobilePointsGeoJSON(date) {
    const { data, error } = await supabase
        .rpc('get_puntos_moviles_geojson', { filter_date: date })
    return data[0]['geojson']
}

export async function retrieveFixedBloodPoints() {
    const fixedKeysTable = 'puntos_fijos_keys';
    let geoJsonData = await fetchFixedPointsGeoJSON();
    let keys = await fetchKeys(fixedKeysTable);
    
    return {
        keys: keys,
        features: geoJsonData?.features?.values()
    }
}

export async function retrieveMobileBloodPointsForDate(date) {
    const mobileKeysTable = 'puntos_moviles_keys';
    let geoJsonData = await  fetchMobilePointsGeoJSON(date);
    let keys = await fetchKeys(mobileKeysTable);
    
    return {
        keys: keys,
        features: geoJsonData?.features?.values()
    }
}

export function filterPointByDate(bloodPoints, filterdDay, filterMonth) {
    let filteredItems = []
    for (const point of bloodPoints) {
        let [day, month] = point.properties.fecha.split('/');
        if (filterdDay === day && filterMonth === month) {
            filteredItems.push(point)
        }
    }
    return filteredItems
}