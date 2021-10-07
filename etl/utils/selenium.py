from urllib.parse import urljoin

from selenium.common.exceptions import NoSuchElementException
import undetected_chromedriver.v2 as uc

URL_BASE = 'http://donarsangre.sanidadmadrid.org/'
URL_PUNTOS_FIJOS = urljoin(URL_BASE, 'fijos.aspx')
URL_PUNTOS_MOVILES = urljoin(URL_BASE, 'moviles.aspx')


def get_uc_driver(headless=True):
    """Get an Undetected Chrome driver for Selenium, optionally headless"""
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")
    options.headless = headless

    return uc.Chrome(options=options)


def get_lista_centros(driver, url):
    driver.get(url)

    button = driver.find_element_by_name(name="ctl00$ctl00$ctl00$MasterCuerpo$MasterCuerpo$ContenedorContenidoSeccion$btnBuscar")
    button.click()

    lista_centros = driver.find_element_by_class_name('ListaCentros')
    
    return lista_centros.find_elements_by_tag_name('li')


def extraer_detalles_punto_fijo(punto_fijo):
    link = punto_fijo.find_element_by_class_name('nombre').find_element_by_tag_name('a')
    details = {
        'name': link.text,
        'url': urljoin(URL_BASE, link.get_attribute('href')),
        'municipality': punto_fijo.find_element_by_class_name('municipio').text.strip()
    }

    return details


def extraer_detalle_centro(elem):
    label = elem.find_element_by_tag_name('label')
    value = elem.find_element_by_class_name('caja_texto')
    if not label or not value:
        return None

    return (label.text.strip(':'), value.text.strip().replace('&nbsp', ''))


def extraer_lat_lng_centro(driver):
    maps_element = driver.find_element_by_partial_link_text('Ampliar el mapa de situación')
    maps_url = maps_element.get_attribute('href')
    lat, lng = maps_url.split('?q=')[1].split('&')[0].split(',+')
    
    return (lat, lng)


def extraer_detalles_centro(driver, name, url):
    driver.get(url)
    id_centro = url.split('ID=')[-1]
        
    details = {'Nombre': name, 'ID del centro': id_centro}
    fields = driver.find_elements_by_class_name('campo')
    for field in fields:
        try:
            detail = extraer_detalle_centro(field)
            details[detail[0]] = detail[1]
        except NoSuchElementException:
            continue
    
    lat, lng = extraer_lat_lng_centro(driver)
    details['latitude'] = lat
    details['longitude'] = lng
    
    return details
