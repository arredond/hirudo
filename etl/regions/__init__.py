"""One module per region (Comunidad Autónoma): scrape, enrich and geocode its
points for the ETL. Raw page parsing lives in utils/crawl/<region>.py; logic
shared across regions in utils/ (geocode.py, points.py, opening_hours.py).
"""
