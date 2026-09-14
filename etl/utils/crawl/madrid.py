"""Crawl Comunidad de Madrid pages and retrieve fixed and mobile blood donation spots."""

import urllib.parse
from io import StringIO

import pandas as pd
import requests
from bs4 import BeautifulSoup

URL_BASE = "https://donarsangre.sanidadmadrid.org/"
URL_FIXED_POINTS = urllib.parse.urljoin(URL_BASE, "fijos.aspx")
URL_MOBILE_POINTS = urllib.parse.urljoin(URL_BASE, "moviles.aspx")

# The "Semáforo de necesidades" component on the national donation site renders
# each blood type with a Bulma background class that encodes how urgently that
# type is needed. Mapping to (status, level) with level 1 = most urgent.
URL_BLOOD_LEVELS = "https://www.donarsangre.org/"
BLOOD_LEVEL_STATUS = {
    "has-background-danger": ("urgent", 1),
    "has-background-warning": ("soon", 2),
    "has-background-success": ("stable", 3),
}

SESSION = requests.Session()


def extract_gmaps_lat_lon(gmaps_url):
    """Extract latitude and longitude from a Google Maps URL.

    Handles formats like: q=40.32246000,+-3.76751960
    """
    parsed = urllib.parse.urlparse(gmaps_url)
    q = urllib.parse.parse_qs(parsed.query)["q"][0]
    # Strip leading + signs that appear before negative coordinates
    lat, lon = [float(x.lstrip("+")) for x in q.split(",")]
    return lat, lon


def extract_fixed_point_general(row):
    """Extract name, ID, and URL from a fixed-point list table row.

    Returns None if the row is not a data row (e.g. header).
    """
    cell = row.find("td", {"data-label": "Nombre:"})
    if not cell:
        return None

    href = cell.find("a").attrs["href"]
    return {
        "name": cell.text.strip(),
        "center_id": href.split("ID=")[-1],
        "url": urllib.parse.urljoin(URL_BASE, href),
    }


def extract_fixed_point_details(url):
    """Fetch a fixed-point detail page and extract its label/value pairs.

    The page uses alternating div.col-form-label elements: even indices are
    labels, odd indices are values.
    Example URL: https://donarsangre.sanidadmadrid.org/detalleCentros.aspx?ID=2544
    """
    response = SESSION.get(url)
    soup = BeautifulSoup(response.text, features="lxml")
    card = soup.find("div", {"class": "card-body"})

    details = {}
    col_divs = card.find_all("div", class_="col-form-label")
    for i in range(0, len(col_divs) - 1, 2):
        key = col_divs[i].text.strip().rstrip(":")
        val = col_divs[i + 1].text.strip()
        details[key] = val

    gmaps_link = soup.find("a", {"id": "ctl00_ContenedorContenidoSeccion_linkGoogle"})
    gmaps_url = gmaps_link.attrs["href"]
    lat, lon = extract_gmaps_lat_lon(gmaps_url)
    details["gmaps_url"] = gmaps_url
    details["latitude"] = lat
    details["longitude"] = lon

    return details


def fetch_points_html(url: str) -> str:
    """Fetch fixed or mobile points HTML via a two-step GET + POST.

    The site is ASP.NET and requires VIEWSTATE tokens obtained from the
    initial GET before the POST form submission will succeed.
    """
    first_response = BeautifulSoup(SESSION.get(url).content, features="lxml")

    data = {
        "ctl00$ContenedorContenidoSeccion$cbxMunicipio": 0,
        "ctl00$ContenedorContenidoSeccion$btnBuscar": "Buscar",
    }
    for key in [
        "__VIEWSTATE",
        "__VIEWSTATEGENERATOR",
        "__VIEWSTATEENCRYPTED",
        "__EVENTVALIDATION",
    ]:
        data[key] = first_response.find("input", {"id": key}).attrs["value"]

    return SESSION.post(url, data).text


def scrape_mobile_points() -> pd.DataFrame:
    """Scrape and return all mobile donation points as a DataFrame."""
    html = fetch_points_html(url=URL_MOBILE_POINTS)
    return pd.read_html(StringIO(html))[0]


def scrape_fixed_points() -> pd.DataFrame:
    """Scrape all fixed donation points, fetching detail pages for each."""
    html = fetch_points_html(url=URL_FIXED_POINTS)
    soup = BeautifulSoup(html, features="lxml")

    panel = soup.find("div", {"class": "panelResultados"})
    fixed_points = []
    for row in panel.find_all("tr"):
        general = extract_fixed_point_general(row)
        if not general:
            continue
        try:
            details = extract_fixed_point_details(general["url"])
            fixed_points.append({**general, **details})
        except Exception:
            print(f"Failed to extract details for {general['url']}")
            raise

    return pd.DataFrame(fixed_points)


def scrape_blood_levels() -> pd.DataFrame:
    """Scrape the "Semáforo de necesidades" blood-reserve levels.

    Reads the semáforo component on https://www.donarsangre.org/ and returns a
    DataFrame with one row per blood type and columns:
    blood_type, status ('urgent'/'soon'/'stable'), level (1-3, 1 = most urgent),
    and label (the original Spanish phrase shown on the site).
    """
    html = SESSION.get(URL_BLOOD_LEVELS).text
    soup = BeautifulSoup(html, features="lxml")

    blood_levels = []
    for item in soup.find("ul", {"class": "semafor-list"}).find_all("li"):
        heading = item.find("h3")
        background_class = next(
            css_class
            for css_class in heading["class"]
            if css_class in BLOOD_LEVEL_STATUS
        )
        status, level = BLOOD_LEVEL_STATUS[background_class]
        blood_levels.append(
            {
                "blood_type": heading.text.strip(),
                "status": status,
                "level": level,
                "label": item.find("p").text.strip(),
            }
        )

    return pd.DataFrame(blood_levels)
