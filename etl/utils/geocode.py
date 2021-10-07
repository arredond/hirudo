import os

from dotenv import load_dotenv
from here_location_services import LS
from googlemaps import Client

load_dotenv()


def here_geocode_row(row):
    """Geocode a 'Punto móvil' row
    
    HERE provides a geocoding score that we can use to filter or warn the user
    """
    ls = LS(api_key=os.environ['HERE_API_KEY'])

    address1 = row.direccion
    address2 = row.ubicacion
    
    results = []
    for address in [address1, address2]:
        full_address = ', '.join([address, row.municipio, 'Community of Madrid', 'Spain'])
        resp = ls.geocode(full_address)
        if not resp.response['items']:
            continue
        first_result = resp.response['items'][0]
        score = first_result['scoring']['queryScore']
        result = {
            'address': full_address,
            'lng': first_result['position']['lng'],
            'lat': first_result['position']['lat'],
            'score': score,
        }
        results.append(result)
    
    if not results:
        print(f'Geocoding failed for {full_address}. No results found')
        return (None, None)
    
    # Select best result
    results_df = pd.DataFrame(results)
    best_result = results_df.loc[results_df['score'].idxmax()]
    if best_result['score'] <= 0.7:
        print(f'Warning. Geocoding for {best_result["full_address"]} received low score of {score}. You may want to double check these results')
    
    lng = best_result['lng']
    lat = best_result['lat']
    
    return (lng, lat)


def google_geocode_address(full_address):
    """Geocode an address.
    
    Google does not provide a score but works much better than competitors
    """
    location_type_scoring = {
        'ROOFTOP': 9,
        'RANGE_INTERPOLATED': 7,
        'GEOMETRIC_CENTER': 6,
        'APPROXIMATE': 4,
    }
    
    gmaps = Client(os.environ['GOOGLE_MAPS_API_KEY'])

    results = gmaps.geocode(full_address)
    if not results:
        print(f'Geocoding failed for {full_address}. No results found')
        return (None, None, None, None)
    
    result = results[0]
    lng = result['geometry']['location']['lng']
    lat = result['geometry']['location']['lat']
    location_type = result['geometry']['location_type']
    score = location_type_scoring[location_type]
    
    return (lng, lat, location_type, score)
