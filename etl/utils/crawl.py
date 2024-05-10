"""Crawl Community of Madrid pages and retrieve fixed and mobile spots"""
import urllib.parse

from io import StringIO

import pandas as pd
import requests

from bs4 import BeautifulSoup


URL_BASE = "https://donarsangre.sanidadmadrid.org/"
URL_PUNTOS_FIJOS = urllib.parse.urljoin(URL_BASE, "fijos.aspx")
URL_PUNTOS_MOVILES = urllib.parse.urljoin(URL_BASE, "moviles.aspx")

URL_IMAGEN = "https://www.comunidad.madrid/servicios/salud/donacion-sangre"

SESSION = requests.Session()


def extract_gmaps_url_lat_lon(gmaps_url):
    """Extract latitude and longitude from a Google Maps URL"""
    parsed_url = urllib.parse.urlparse(gmaps_url)
    params = urllib.parse.parse_qs(parsed_url.query)
    lat, lon = [float(x) for x in params["q"][0].split(", ")]
    return lat, lon


def extraer_detalles_generales_pf(panel_row):
    """Extract details from the fixed points panel"""
    cell_name = panel_row.find("td", {"data-label": "Nombre:"})
    if not cell_name:
        return None

    href = cell_name.find("a").attrs["href"]
    details = {
        "nombre": cell_name.text.strip(),
        "id_del_centro": href.split("ID=")[-1],
        "url": urllib.parse.urljoin(URL_BASE, href),
    }

    return details


def extraer_detalles_concretos_pf(url):
    """Extract details for a fixed point"""
    rpf = SESSION.get(url)
    rpf_html = BeautifulSoup(rpf.text, features="lxml")
    tabla_detalles = rpf_html.find("div", {"class": "divTableMsg"})
    detalles_centro = {}
    # Extraer filas y columnas en formato horrible
    for div in tabla_detalles.find_all("div"):
        labels = div.find_all("label")
        if not len(labels) == 1:
            continue

        key = labels[0].text
        val = div.find("div", {"class": "labelValue"}).text
        detalles_centro[key] = val

    # Extraer URL de Google Maps y lat/lon
    gmaps_url = rpf_html.find(
        "a", {"id": "ctl00_ContenedorContenidoSeccion_linkGoogle"}
    ).attrs["href"]
    lat, lon = extract_gmaps_url_lat_lon(gmaps_url)
    detalles_centro["gmaps_url"] = gmaps_url
    detalles_centro["latitude"] = lat
    detalles_centro["longitude"] = lon

    return detalles_centro


def pedir_html_puntos(url: str) -> str:
    """Listar puntos fijos o móviles

    En ambos casos, antes de mandar un formulario por POST hay que hacer
    un GET y pillar algunos códigos internos (ejemplo: __VIEWSTATE)
    """
    # First GET request will get us the pseudo-auth codes
    r1_html = BeautifulSoup(SESSION.get(url).content, features="lxml")

    # Second POST request actually submits the form to fetch results
    data = {
        "ctl00$ContenedorContenidoSeccion$cbxMunicipio": 0,
        "ctl00$ContenedorContenidoSeccion$btnBuscar": "Buscar",
    }
    internal_code_keys = ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__EVENTVALIDATION"]
    for k in internal_code_keys:
        data[k] = r1_html.find("input", {"id": k}).attrs["value"]

    return SESSION.post(url, data).text


def extraer_puntos_moviles():
    """Extraer puntos móviles

    Si no se dan argumentos de municipio y fecha se devuelven todos.
    Los puntos móviles no tienen página de atributos adicionales.
    Usamos pandas para parsear el HTML directamente ya que es una tabla simple
    """
    html_txt = pedir_html_puntos(url=URL_PUNTOS_MOVILES)
    return pd.read_html(StringIO(html_txt))[0]


def extraer_puntos_fijos():
    """Extraer puntos fijos

    Cada punto fijo tiene una URL propia (por hospital) con detalles adicionales.
    No podemos usar Pandas para parsear el HTML porque pierde las URLs de los hospitales,
    así que hay que hacerlo a mano.
    """
    html_txt = pedir_html_puntos(url=URL_PUNTOS_FIJOS)
    html = BeautifulSoup(html_txt, features="lxml")

    panel_resultados = html.find("div", {"class": "panelResultados"})
    panel_rows = panel_resultados.find_all("tr")

    puntos_fijos = []
    for panel_row in panel_rows:
        if detalles_pf := extraer_detalles_generales_pf(panel_row):
            # Fetch additional details from hospital page
            detalles_url = extraer_detalles_concretos_pf(detalles_pf["url"])
            detalles_pf = {**detalles_pf, **detalles_url}

            puntos_fijos.append(detalles_pf)

    return pd.DataFrame(puntos_fijos)


def get_gmaps_url(row):
    """Compose Google Maps URL"""
    return f"https://www.google.com/maps?q={row.latitude}+{row.longitude}"
