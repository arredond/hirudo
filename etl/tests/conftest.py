"""Shared fixtures for the ETL test suite."""

DETAIL_PAGE_HTML = """
<html><body>
<div class="card-body">
  <div class="row">
    <div class="col-lg-8">
      <div class="row" id="ctl00_ContenedorContenidoSeccion_divHorarioDonaciones">
        <div class="col-form-label col-sm-5">Horario de donaciones:</div>
        <div class="col-form-label col-sm-7 font-weight-bold">Lunes a sábado de 9:00 a 20:30 h</div>
      </div>
      <div class="row">
        <div class="col-form-label col-sm-5">Ubicación de las salas de donación:</div>
        <div class="col-form-label col-sm-7 font-weight-bold">Planta baja, Zona C</div>
      </div>
      <div class="row">
        <div class="col-form-label col-sm-5">Dirección postal:</div>
        <div class="col-form-label col-sm-7 font-weight-bold">AVDA ORELLANA, 1</div>
      </div>
      <div class="row">
        <div class="col-form-label col-sm-5">Municipio:</div>
        <div class="col-form-label col-sm-7 font-weight-bold">Leganés</div>
      </div>
    </div>
  </div>
</div>
<a id="ctl00_ContenedorContenidoSeccion_linkGoogle"
   href="https://maps.google.com/maps?q=40.32246000,+-3.76751960&amp;iwloc=A&amp;hl=es">
  Mapa
</a>
</body></html>
"""

SEMAFORO_PAGE_HTML = """
<html><body>
<div class="semaforo-box flow flow--4">
  <div class="flow">
    <h2 class="is-size-6">Semáforo de necesidades</h2>
    <ul role="list" class="semafor-list is-flex is-flex-wrap-wrap">
      <li class="has-text-centered">
        <h3 class="is-flex has-background-danger has-text-white rounded">0-</h3>
        <p class="is-size-9 has-text-weight-bold has-text-danger">Dona hoy</p>
      </li>
      <li class="has-text-centered">
        <h3 class="is-flex has-background-warning has-text-black rounded">A+</h3>
        <p class="is-size-10">Dona en los <strong>próximos días</strong></p>
      </li>
      <li class="has-text-centered">
        <h3 class="is-flex has-background-success has-text-white rounded">AB+</h3>
        <p class="is-size-10">Dona dentro de <strong>unas semanas</strong></p>
      </li>
    </ul>
  </div>
</div>
</body></html>
"""

LIST_PAGE_HTML = """
<html><body>
<div class="panelResultados">
  <table>
    <tr>
      <th>Nombre</th><th>Municipio</th>
    </tr>
    <tr>
      <td data-label="Nombre:"><a href="detalleCentros.aspx?ID=2544">Hospital Severo Ochoa</a></td>
      <td data-label="Municipio:">Leganés</td>
    </tr>
    <tr>
      <td data-label="Nombre:"><a href="detalleCentros.aspx?ID=2545">Hospital Santa Cristina</a></td>
      <td data-label="Municipio:">Madrid</td>
    </tr>
  </table>
</div>
</body></html>
"""

# Trimmed from https://www.centrodehemoterapiacyl.es/puntos-de-donacion/avila/ —
# the fixed point's schedule spans several rows via a rowspan'd first cell.
CYL_PROVINCE_PAGE_HTML = """
<html><body>
<div class="entry-content">
  <table>
    <tbody>
      <tr>
        <th>PUNTO FIJO DE DONACIÓN DE ÁVILA</th>
        <th colspan="2">HORARIO</th>
      </tr>
      <tr>
        <td rowspan="3">
          <strong>HOSPITAL PROVINCIA DE ÁVILA</strong><br/>
          C/ Jesús del Gran Poder, 44
          <a href="https://maps.app.goo.gl/hRDcjSERk7mN4TSaA">Ver Ubicación</a><br/>
          05004 Ávila
        </td>
      </tr>
      <tr><td>Martes y Jueves</td><td>15.00 a 21.30 h</td></tr>
      <tr><td>Viernes</td><td>09.30 a 15.00 h</td></tr>
      <tr>
        <td align="right" colspan="3"><p><span>Festivos cerrado.</span></p></td>
      </tr>
    </tbody>
  </table>
  <table>
    <thead>
      <tr>
        <th>Campañas de donación</th>
        <th>Fecha - Ubicación</th>
        <th>Horario</th>
        <th>Dirección</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>EL HOYO DE PINARES</td>
        <td>14/09/2026 Consultorio Médico</td>
        <td>De 16:30 a 20:30</td>
        <td>
          Plaza Víctimas del Terrorismo El Hoyo de Pinares (AVILA)
          <a href="https://maps.google.es/maps?q=x">Ver Ubicación</a>
        </td>
      </tr>
    </tbody>
  </table>
</div>
</body></html>
"""

# Trimmed from https://www.centrodehemoterapiacyl.es/ — the "Niveles de
# sangre actuales" widget, one box per blood type.
CYL_HOME_PAGE_HTML = """
<html><body>
<div class="column mcb-column one-fourth" title="Nivel Óptimo A+">
  <div class="column_attr"><h2><i class="icon-droplet" style="color:#45a81e"></i>A+</h2></div>
</div>
<div class="column mcb-column one-fourth" title="Nivel Medio A-">
  <div class="column_attr"><h2><i class="icon-droplet" style="color:#fe940d"></i>A-</h2></div>
</div>
<div class="column mcb-column one-fourth" title="Nivel Bajo B+">
  <div class="column_attr"><h2><i class="icon-droplet" style="color:#e85e5e"></i>B+</h2></div>
</div>
</body></html>
"""

# Trimmed from
# https://sanidad.castillalamancha.es/ciudadanos/hazte-donante-sangre/puntos-fijos-de-donacion
# — a Drupal Views accordion, one row per fixed point. Includes a repeated
# locality (Toledo) and an address with no trailing period (Ciudad Real) —
# both real edge cases the source data has.
CLM_FIXED_POINTS_HTML = """
<html><body>
<div class="views-row">
  <div class="views-field views-field-title views-accordion-header">
    <span class="field-content">ALBACETE</span>
  </div>
  <div class="views-field views-field-field-direccion">
    <div class="field-content"><p><strong>Dirección:</strong>
      Hospital General Universitario. C/. Hermanos Falcó, 37.</p></div>
  </div>
  <div class="views-field views-field-body">
    <div class="field-content">
      <p><strong>Horario</strong></p>
      <p>Lunes a viernes de 8:30 a 14:00 h.</p>
    </div>
  </div>
  <div class="views-field views-field-field-telefonos-contacto">
    <div class="field-content"><p><strong>Teléfono:</strong> 967 24 30 72</p></div>
  </div>
</div>
<div class="views-row">
  <div class="views-field views-field-title views-accordion-header">
    <span class="field-content">CIUDAD REAL</span>
  </div>
  <div class="views-field views-field-field-direccion">
    <div class="field-content"><p><strong>Dirección:</strong>
      Hospital General Universitario de Ciudad Real</p></div>
  </div>
  <div class="views-field views-field-body">
    <div class="field-content">
      <p><strong>Horario</strong></p>
      <p>Lunes a Viernes de 9:00 horas a 14:30 horas</p>
    </div>
  </div>
  <div class="views-field views-field-field-telefonos-contacto">
    <div class="field-content"><p><strong>Teléfono:</strong> 926 213 446</p></div>
  </div>
</div>
<div class="views-row">
  <div class="views-field views-field-title views-accordion-header">
    <span class="field-content">TOLEDO</span>
  </div>
  <div class="views-field views-field-field-direccion">
    <div class="field-content"><p><strong>Dirección:</strong>
      Hospital Universitario de Toledo - Servicio de Transfusión.</p></div>
  </div>
  <div class="views-field views-field-body">
    <div class="field-content">
      <p><strong>Horario</strong></p>
      <p>Lunes a viernes, de 9:00 a 14:00 h.</p>
    </div>
  </div>
  <div class="views-field views-field-field-telefonos-contacto">
    <div class="field-content"><p><strong>Teléfono:</strong> 925 26 92 00</p></div>
  </div>
</div>
<div class="views-row">
  <div class="views-field views-field-title views-accordion-header">
    <span class="field-content">TOLEDO</span>
  </div>
  <div class="views-field views-field-field-direccion">
    <div class="field-content"><p><strong>Dirección:</strong>
      Centro San Ildefonso. Avenida Barber 26, Toledo</p></div>
  </div>
  <div class="views-field views-field-body">
    <div class="field-content">
      <p><strong>Horario</strong></p>
      <p>Lunes a viernes, de 9:00 a 14:30 h.</p>
      <p>WhatsApp: 656 555 781</p>
      <p>Email: donasangretoledo1@gmail.com</p>
    </div>
  </div>
  <div class="views-field views-field-field-telefonos-contacto">
    <div class="field-content"><p><strong>Teléfono:</strong> 656 555 781</p></div>
  </div>
</div>
</body></html>
"""

# Trimmed from
# https://sanidad.castillalamancha.es/ciudadanos/hazte-donante-sangre/colectas-donantes-de-sangre/toledo
# — a Drupal Views table, page 1 of 2 (has a pager-next link to page 2).
CLM_MOBILE_PAGE1_HTML = """
<html><body>
<table class="views-table cols-5">
  <thead><tr><th>Día</th><th>Horario</th><th>Localidad</th>
    <th>Lugar de la Colecta</th><th>Tipo de donación</th></tr></thead>
  <tbody>
    <tr>
      <td><span class="date-display-single">Lunes, 14 Septiembre, 2026</span></td>
      <td>17:00-20:30</td>
      <td>PUEBLA DE MONTALBAN,LA</td>
      <td>Centro de Salud</td>
      <td>SANGRE</td>
    </tr>
  </tbody>
</table>
<ul class="pager clearfix">
  <li class="pager-next"><a href="/ciudadanos/hazte-donante-sangre/colectas-donantes-de-sangre/toledo?page=1">&rsaquo;</a></li>
</ul>
</body></html>
"""

CLM_MOBILE_PAGE2_HTML = """
<html><body>
<table class="views-table cols-5">
  <thead><tr><th>Día</th><th>Horario</th><th>Localidad</th>
    <th>Lugar de la Colecta</th><th>Tipo de donación</th></tr></thead>
  <tbody>
    <tr>
      <td><span class="date-display-single">Martes, 15 Septiembre, 2026</span></td>
      <td>16:00-20:00</td>
      <td>CONSUEGRA</td>
      <td>(SÓLO PLASMA) Centro de Salud</td>
      <td>PLASMA</td>
    </tr>
  </tbody>
</table>
<ul class="pager clearfix">
  <li class="pager-current last">2</li>
</ul>
</body></html>
"""

# Trimmed from https://bancosangrearagon.org/ — the homepage's "Puntos fijos
# de donación" Elementor text widget: an <h4> per province, then a <ul> with
# the center name in <strong> and everything else as free text.
ARAGON_HOME_HTML = """
<html><body>
<div class="elementor-element puntos-fijos elementor-widget elementor-widget-text-editor">
  <div class="elementor-widget-container">
    <h4>ZARAGOZA</h4>
    <ul>
      <li><strong>Banco de Sangre y Tejidos de Aragón</strong>
        C/ Ramón Salanova,1, esquina Duquesa Villahermosa.&nbsp; Parking gratuito.&nbsp;
        Teléfono: 876 764 300.&nbsp; Horario: de lunes a viernes de 8:00 h. a 21:00 h.
        Sábados 8:30 h. a 14:00 h.</li>
      <li><strong>Hospital Miguel Servet</strong>
        Pº Isabel la Católica, 1-3. Teléfono: 976 765 500.&nbsp; Horario: de lunes a
        viernes de 9:00 h. a 13:00 h. Servicio de Hematología-Transfusiones&nbsp; 4ª
        planta.</li>
    </ul>
    <h4>TERUEL</h4>
    <ul>
      <li><strong>Hospital Obispo Polanco</strong>
        Ruiz Jarabo, s/n. Teléfono: 978 621 150.&nbsp; Horario: de lunes a jueves de
        10:30 h. a 14:00 h.</li>
    </ul>
  </div>
</div>
</body></html>
"""


def aragon_event(event_id: int, title: str, start: str, end: str) -> dict:
    """Build a minimal Events Calendar REST API event, trimmed to the fields
    the Aragón crawler reads."""
    return {
        "id": event_id,
        "url": f"https://bancosangrearagon.org/extraccion/{event_id}/",
        "title": title,
        "start_date": start,
        "end_date": end,
        "venue": [],
    }


# Trimmed from
# https://centro-transfusion.san.gva.es/es/puntos-de-donacion?provincia=castellon
# — the fixed-points list, then a per-date schedule table. Includes the
# fixed point's own schedule row, a morning/afternoon pair for the same stop
# (two rows), a "(SOLO EMPLEADOS)" stop, a plasma-only stop, and a
# hyphenated town ("VILA-REAL") — all real quirks of the source data.
def valencia_row(poblacion: str, ubicacion: str, horario: str) -> str:
    """Build one schedule <tr>, including the mobile-only label prefixes."""
    return f"""
      <tr>
        <td class="textotabla2sincursor poblacion"><b class="d-lg-none">Población:</b> {poblacion}</td>
        <td class="textotabla2sincursor ubicacion"><b class="d-lg-none">Ubicación:</b> {ubicacion}</td>
        <td class="textotabla2sincursor horario"><b class="d-lg-none">Horario:</b> {horario}</td>
      </tr>"""


VALENCIA_HEADER_ROW = """
      <tr class="d-none d-lg-table-row">
        <td class="titulotabla"><b>Población</b></td>
        <td class="titulotabla"><b>Ubicación</b></td>
        <td class="titulotabla"><b>Horario</b></td>
      </tr>"""

VALENCIA_FIXED_UBICACION = (
    "CASTELLÓN-CENTRO DE TRANSFUSIÓN C.V. SALA DONACIÓN-PARKING SUBTERRÁNEO "
    "HOSP.GRATUITO, AVDA. BENICASIM, S/N"
)

VALENCIA_PROVINCE_PAGE_HTML = f"""
<html><body>
<table class="text-left ctfcv"><tr><td class="datos">
<table><tr><td class="texto">
  <p class="subtitulo1">Puntos Fijos de extracción</p>
  <div class="puntosfijos">
    <p class="subtitulo2">CASTELLÓN-CENTRO DE TRANSFUSIÓN C.V. SALA  DONACIÓN-PARKING SUBTERRÁNEO HOSP.GRATUITO, AVDA. BENICASIM, S/N</p>
    <p>12004-CASTELLÓ DE LA PLANA</p>
    <p></p>
    <p>Horarios sujetos a la programación de las donaciones (Ver a continuación)</p>
  </div>
  <p class="subtitulo1">Programación de las Donaciones</p>
  <p class="subtitulo2">Martes, 27 de octubre</p>
  <table class="datosCentro">{VALENCIA_HEADER_ROW}
    {valencia_row("CASTELLÓ DE LA PLANA", VALENCIA_FIXED_UBICACION, "08:30-14:00")}
    {valencia_row("CASTELLÓ DE LA PLANA", VALENCIA_FIXED_UBICACION, "14:00-21:00")}
    {valencia_row("CABANES", "CABANES-CASAL JOVE LOCAL, CARRER  DELEGADO VALERA, N. 50", "16:30-20:30")}
    {valencia_row("VILA-REAL", "VILA-REAL - HOSPITAL LA PLANA HALL PRINCIPAL, CTRA. VILA-REAL A BURRIANA, KM. 0.5", "16:30-20:30")}
    {valencia_row("VILA-REAL", "VILA-REAL - HOSPITAL LA PLANA HALL PRINCIPAL, CTRA. VILA-REAL A BURRIANA, KM. 0.5", "09:30-13:30")}
  </table>
  <p class="subtitulo2">Miércoles, 28 de octubre</p>
  <table class="datosCentro">{VALENCIA_HEADER_ROW}
    {valencia_row("CASTELLÓ DE LA PLANA", VALENCIA_FIXED_UBICACION, "08:30-14:30")}
    {valencia_row("CASTELLÓ DE LA PLANA", "CASTELLÓN-PROP (SOLO EMPLEADOS), AVDA. HERMANOS BOU, S/N", "09:30-13:30")}
    {valencia_row("ELCHE", "ELCHE-SOLO DONACIÓN DE PLASMA CON CITA PREVIA-ELCHE HOSPITAL GENERAL , C/ ALMAZARA Nº 11", "16:30-21:00")}
  </table>
</td></tr></table>
</td></tr></table>
</body></html>
"""

# Trimmed from https://www.bancsang.net/es/donaciones/sangre/donde/ — one
# card per hospital with a blood and a plasma booking button.
CATALUNA_DONDE_HTML = """
<html><body>
<div class="column">
  <h3>Barcelona</h3><p>Hospital de la Santa Creu i Sant Pau</p>
  <a href="/es/donaciones/sangre/hospital/c/2/">Dona sangre</a>
  <a href="/es/donaciones/plasma/inscripcion//?hospital=99999">Dona plasma</a>
</div>
<div class="column">
  <h3>Hospitalet de Llobregat, L'</h3><p>BST L’Hospitalet - Santa Eulàlia</p>
  <a href="/es/donaciones/sangre/hospital/c/30/">Dona sangre</a>
  <a href="/es/donaciones/sangre/hospital/c/30/28-10-2026/">28</a>
</div>
</body></html>
"""

# Trimmed from https://www.bancsang.net/es/hospitales/30/bst-l-hospitalet-santa-eulalia
CATALUNA_HOSPITAL_INFO_HTML = """
<html><body>
<h1>BST L’Hospitalet - Santa Eulàlia</h1>
<div class="flow flow--small text-base">
  <h3 class="is-relative is-size-7"><svg></svg>Horario</h3>
  <div class="is-size-8">
    <p>De lunes a viernes de 9 a 20 h.<br/>Sábados de 9 a 14.30 h.</p>
    <p>El <strong>20 de octubre</strong> la donación estará cerrada de 15 a 16h.</p>
  </div>
  <h3 class="is-relative is-size-7"><svg></svg>Ubicación</h3>
  <div class="is-size-8">
    C/ Jacint Verdaguer, 12
    <p>08902\t\t\t\t\t\tHospitalet de Llobregat, L'</p>
    <p class="is-flex"><svg></svg>93 557 36 41</p>
    <p class="mt-4"><a href="https://www.google.com/maps/dir//...">Cómo llegar</a></p>
  </div>
</div>
</body></html>
"""

# Trimmed from https://www.bancsang.net/es/donaciones/sangre/calendario-de-recogida/
# — one grid of cards per day: a blood-only stop, a blood + plasma stop, a
# plasma-only stop (no blood button), and a donation-bus stop.
CATALUNA_CALENDAR_HTML = """
<html><body>
<div class="boxes-grid columns">
  <div class="column is-half-mobile"><div>
    <h3 class="is-size-8 mt-3">Barcelona</h3>
    <p>Escola Santa Anna<br/>C. Bailèn, 53</p>
    <ul><li><a class="button is-primary" href="/es/donaciones/sangre/recogida/poblacion//9386/barcelona/27-10-2026/">Dona sangre</a></li></ul>
  </div></div>
  <div class="column is-half-mobile"><div>
    <h3 class="is-size-8 mt-3">Esparreguera</h3>
    <p>Biblioteca l'Ateneu<br/>Pl. Antoni Nin i Escudé, 1</p>
    <ul>
      <li><a class="button is-primary" href="/es/donaciones/sangre/recogida/poblacion//13445/esparreguera/27-10-2026/">Dona sangre</a></li>
      <li><a class="button is-plasma" href="/es/donaciones/plasma/inscripcion/?hospital=534K&amp;day=27-10-2026">Dona plasma</a></li>
    </ul>
  </div></div>
  <div class="column is-half-mobile"><div>
    <h3 class="is-size-8 mt-3">Vielha e Mijaran</h3>
    <p>Palau d'Esports<br/>Av. Garona, 35</p>
    <ul><li><a class="button is-plasma" href="/es/donaciones/plasma/inscripcion/?hospital=9B243&amp;day=27-10-2026">Dona plasma</a></li></ul>
  </div></div>
</div>
<div class="boxes-grid columns">
  <div class="column is-half-mobile"><div>
    <h3 class="is-size-8 mt-3">Gavà</h3>
    <p>Unidad móvil<br/>Pl. Jaume Balmes</p>
    <ul><li><a class="button is-primary" href="/es/donaciones/sangre/recogida/poblacion//14001/gava/28-10-2026/">Dona sangre</a></li></ul>
  </div></div>
</div>
</body></html>
"""

# Trimmed from a stop's blood-booking page (e.g. .../poblacion//9386/barcelona/27-10-2026/)
CATALUNA_STOP_HTML = """
<html><body><div class="text">
  <p class="seleccio">Barcelona</p>
  <p class="seleccio b">Tuesday, 27 de October de 2026</p>
  <p class="horari">
      De 10:00 a 14:00 i de 16:00 a 21:00
  </p>
  <p class="lloc">Escola Santa Anna, C. Bailèn, 53</p>
</div></body></html>
"""

# Trimmed from https://ados.sergas.gal/cartafol/ADOS-locais (two of seven
# accordion blocks: one with GPS coordinates, one without)
GALICIA_FIXED_POINTS_HTML = """
<html><body>
<div class="accordion-simple"><div class="accordion-content-block collapse"><div class="accordion-content-block-title">
  <span>Local de doazón de Ferrol</span> </div><div class="accordion-content-block-data"><p>
  <b>Horario</b></p><p>Luns de 15&#58;00 a 22&#58;00</p><p>Martes, mércores e xoves de 8&#58;00 a 15&#58;00<br></p><p>
  <b>\u200bEnderezo</b></p><p>Hospital Arquitecto Marcide. Andar cero<br></p><p>Estrada de San Pedro de Leixa, s/n</p><p>15405 Ferrol</p><p>Teléfono 981334541</p><p>Aparcamento gratuíto no parking do hospital</p><p>Coordenadas GPS&#58; 43°30'37.0&quot;N 8°12'58.2&quot;W.</p></div></div></div>
<div class="accordion-simple"><div class="accordion-content-block collapse"><div class="accordion-content-block-title">
  <span>Local de doazón de Ourense</span></div>
  <div class="accordion-content-block-data"><p>\u200b<b>Horario</b></p><p>
  <span style="text-decoration&#58;underline;">Horario de inverno</span> (de outubro a maio)</p><p>Luns e&#160;venres&#160;de 15&#58;00 a 22&#58;00\u200b</p><p>
  <b>Enderezo</b></p><p>Plaza Paz Novoa nº3.&#160;Aparcamento gratuíto &quot;parking Orense&quot;\u200b</p><p>32003 Ourense</p><p>Teléfono 988370103</p></div></div></div>
<div class="accordion-simple"><div class="accordion-content-block collapse"><div class="accordion-content-block-title">
  <span>Local de doazón de Santiago</span> </div><div class="accordion-content-block-data"><p>
  <b>Horario</b></p><p>Luns a venres de 8&#58;00 a 22&#58;00</p><p>
  <b>Enderezo</b></p><p>Complexo Hospitalario Universitario de Santiago (CHUS)</p><p>Teléfono 981955728</p><p>Coordenadas GPS&#58; 42º 52' 8.7''N 8º 33' 55.1''WOs.</p></div></div></div>
</body></html>
"""

# Trimmed from https://ados.sergas.gal/cartafol/proximos-desprazamentos
GALICIA_MOBILE_POINTS_HTML = """
<html><body><div class="collect-container"><div class="collect-body">
<details class="group-details"><summary>ÁREA SANITARIA A CORUÑA E CEE</summary><div class="group-content">
<div class="date-header">Venres, 23/10/2026&#160;</div><div class="table-wrapper"><table class="collect-table">
<thead><tr><th>Concello</th><th>Lugar de colecta</th><th>Localizacións e horarios</th></tr></thead><tbody>
<tr><td><strong>Sada</strong></td><td><strong>SADA</strong> </td><td><div class="location-item"><span class="location-name">UNIDADE MÓBIL DIANTE DA CASA DA XUVENTUDE</span> <span class="schedule-time">09&#58;45 a 14&#58;30 e 15&#58;45 a 21&#58;00</span>&#160;</div></td></tr>
</tbody></table>&#160;</div>
</div></details>
<details class="group-details"><summary>ÁREA SANITARIA LUGO-A MARIÑA-MONFORTE</summary><div class="group-content">
<div class="date-header">Martes, 10/11/2026&#160;</div><div class="table-wrapper"><table class="collect-table">
<thead><tr><th>Concello</th><th>Lugar de colecta</th><th>Localizacións e horarios</th></tr></thead><tbody>
<tr class="provisional-row"><td><strong>Foz</strong></td><td><strong>FOZ</strong> <span class="provisional-badge">Provisional</span></td><td><div class="location-item"><span class="location-name">PRAZA CONDE FONTAO
NO PEIRAO (AO CARON DA FUNCIONAL)</span> <span class="schedule-time">10&#58;30 a 14&#58;00 e 16&#58;30 a 21&#58;00</span>&#160;</div><div class="location-item"><span class="location-name">Localización 2</span> <span class="schedule-time">16&#58;30 a 21&#58;00</span></div></td></tr>
</tbody></table>&#160;</div>
<div class="date-header">Luns, 02/11/2026&#160;</div><div class="table-wrapper"><table class="collect-table">
<thead><tr><th>Concello</th><th>Lugar de colecta</th><th>Localizacións e horarios</th></tr></thead><tbody>
<tr><td><strong>Melón</strong></td><td><strong>MELON</strong> </td><td><div class="location-item"><span class="location-name">QUINS: UNIDADE MOBIL DIANTE DO CENTRO DE SAÚDE</span> <span class="schedule-time">10&#58;00 a 11&#58;30</span></div><div class="location-item"><span class="location-name">MELON: UNIDADE MOBIL NO PARQUE DE MELON</span> <span class="schedule-time">12&#58;00 a 14&#58;00</span></div></td></tr>
</tbody></table>&#160;</div>
</div></details>
</div></div></body></html>
"""

GALICIA_SEMAFORO_HTML = """
<html><body><div class="carousel-item active"><a href="#">
<img src="/cartafol/PublishingImages/148/Semaforo_2026-10-20.png" alt="Visor Semáforo" class="d-block" />
</a></div><img src="/cartafol/PublishingImages/148/acceso-sema3.png" alt="Semáforo" /></body></html>
"""

# Trimmed from the "¿Dónde donar?" day-listing endpoint
# (.../extracciones/index.php?idioma=ES&provincia=Bizkaia&fechaInicio=2026/10/27):
# a fixed centre, a stop open morning and afternoon (listed twice), and an
# exact repeat.
PAIS_VASCO_DAY_HTML = (
    '<div class="contenedor_Bizkaia"><span class="lugar" style="text-transform:uppercase">'
    'Galdakao:</span> <span class="lugar">GALDAKAO Planta 0-CVTTH</span><br/>27-10 de 8:30 '
    'a 14:30<br/><a class="direccion" href="https://www.google.com/maps/place/'
    '43.222799979715,-2.8175108989617" target="_blank">Barrio Labeaga 46A </a></span></div>'
    '<div class="contenedor_Bizkaia"><span class="lugar" style="text-transform:uppercase">'
    'Bilbao:</span> <span class="lugar">Bilbao Bombero Etxaniz - Solo Plasma/Cita</span>'
    '<br/>27-10 de 8:30 a 13:00<br/><a class="direccion" href="https://www.google.com/maps/'
    'place/43.258362392224,-2.939835762394" target="_blank">Plaza Bombero Etxaniz 1</a>'
    "</span></div>"
    '<div class="contenedor_Bizkaia"><span class="lugar" style="text-transform:uppercase">'
    'Bilbao:</span> <span class="lugar">Bilbao Bombero Etxaniz - Solo Plasma/Cita</span>'
    '<br/>27-10 de 14:00 a 18:30<br/><a class="direccion" href="https://www.google.com/maps/'
    'place/43.258362392224,-2.939835762394" target="_blank">Plaza Bombero Etxaniz 1</a>'
    "</span></div>"
    '<div class="contenedor_Bizkaia"><span class="lugar" style="text-transform:uppercase">'
    'Bilbao:</span> <span class="lugar">Plaza Circular</span><br/>27-10 de 9:15 a 14:00<br/>'
    '<a class="direccion" href="https://www.google.com/maps/place/43.26128769,-2.92748213" '
    'target="_blank">Plaza Circular</a></span></div>'
    '<div class="contenedor_Bizkaia"><span class="lugar" style="text-transform:uppercase">'
    'Bilbao:</span> <span class="lugar">Plaza Circular</span><br/>27-10 de 9:15 a 14:00<br/>'
    '<a class="direccion" href="https://www.google.com/maps/place/43.26128769,-2.92748213" '
    'target="_blank">Plaza Circular</a></span></div>'
)

# Trimmed from .../niveles-sangre/index.php?idioma=ES
PAIS_VASCO_LEVELS_HTML = (
    '<p class="linea_niveles"><span class="fecha_niveles"> 27/10/2026</span></p>'
    '<table class="tabla_niveles"><tr>'
    '<td class="row_niveles"><img src="https://donantesdesangre.eus/wp-content/themes/'
    'hello-elementor/niveles-sangre/Reserva-Sangre-02.svg" alt="O+" class="bolsa_sangre" />'
    "<br/>O+</td>"
    '<td class="row_niveles"><img src="https://donantesdesangre.eus/wp-content/themes/'
    'hello-elementor/niveles-sangre/Reserva-Sangre-03.svg" alt="O-" class="bolsa_sangre" />'
    "<br/>O-</td>"
    '<td class="row_niveles"><img src="https://donantesdesangre.eus/wp-content/themes/'
    'hello-elementor/niveles-sangre/Reserva-Sangre-01.svg" alt="B+" class="bolsa_sangre" />'
    "<br/>B+</td></tr></table>"
    '<table class="tabla_niveles"><tr><td class="row_niveles"><img src="https://'
    "donantesdesangre.eus/wp-content/themes/hello-elementor/niveles-sangre/"
    'ico-sangre-roja.svg" /></td><td class="texto_donar">Dona urgente</td></tr></table>'
)


# Trimmed from https://www.hdsc.org/ — the homepage's "dónde donar" slider
# (a Revolution Slider module). Only the Banco's slide carries a Google Maps
# link; the e-mail slide and the activities slide are the distractors.
CANTABRIA_HOME_HTML = """
<html><body>
<sr7-module data-alias="donar-1" data-id="20" id="SR7_20_2" class="rs-ov-hidden" data-version="6.7.58">
  <sr7-adjuster></sr7-adjuster>
  <sr7-content>
  <sr7-carousel>
  <sr7-slide id="SR7_20_2-8" data-key="8">
  <p id="SR7_20_2-8-1" class="sr7-layer"><a href="https://maps.app.goo.gl/UwoRmWBNeAMJKgKMA" style="text-decoration:none; color:#f5333f;"  target="_blank">Avenida de Valdecilla s/n.<br />
Pabellón 13, Planta 0<br />
Santander</a><br />
<br />
T. <a href="tel:+34942202689" style="text-decoration:none;color:#f5333f;">942 202 689</a></p>
  <h2 id="SR7_20_2-8-2" class="sr7-layer">dónde donar</h2>
  <h3 id="SR7_20_2-8-3" class="sr7-layer">Banco de Sangre y Tejidos del Hospital Universitario Marqués de Valdecilla</h3>
  <p id="SR7_20_2-8-4" class="sr7-layer">Puedes acudir directamente o pedir cita previa en la aplicación si no quieres esperar.<br />
<br />
Estamos de <strong>lunes a viernes </strong> de <strong>8:30 a 21:00h</strong>.</p>
  </sr7-slide>
  <sr7-slide id="SR7_20_2-9" data-key="9">
  <p id="SR7_20_2-9-1" class="sr7-layer"><a href="mailto:hermandad@hdsc.org" style="text-decoration:none;color:#f5333f;">hermandad@hdsc.org</a><br />
<br />
T. <a href="tel:+34942202689" style="text-decoration:none;color:#f5333f;">942 202 689</a></p>
  <h2 id="SR7_20_2-9-2" class="sr7-layer">dónde donar</h2>
  <h3 id="SR7_20_2-9-3" class="sr7-layer">Organiza eventos o<br />
campañas especiales</h3>
  <p id="SR7_20_2-9-4" class="sr7-layer">Si quieres organizar un evento o campañas especiales de donación en tu organización o comunidad ponte en contacto con nosotros. Estaremos encantados de ampliar las campañas de nuestra red de colaboradores.</p>
  </sr7-slide>
  <sr7-slide id="SR7_20_2-10" data-key="10">
  <p id="SR7_20_2-10-1" class="sr7-layer"><a href="https://www.hdsc.org/actividades/" style="text-decoration:none; color:#f5333f;">Consulta el calendario de unidades móviles</a></p>
  <h2 id="SR7_20_2-10-2" class="sr7-layer">dónde donar</h2>
  <h3 id="SR7_20_2-10-3" class="sr7-layer">Unidades móviles</h3>
  <p id="SR7_20_2-10-4" class="sr7-layer">que se desplazan a diferentes puntos de la región. Consulta el calendario y los  lugares donde estará en los próximos días.</p>
  </sr7-slide>
  <sr7-slide id="SR7_20_2-14" data-key="14">
  </sr7-slide>
  </sr7-carousel>
  </sr7-content>
    </sr7-module>
</body></html>
"""
# Trimmed from https://adona.es/es/contacto-adona/contacto-tudela: the info
# boxes (address, phone, hours) and the map script with the spot's centre.
NAVARRA_CONTACT_TUDELA_HTML = """
<div class="block block-contact">
  <div class="box-services-2">
    <div class="box-left"><i class="icon icon-4 icon_pin_alt"></i></div>
    <div class="box-right">
      C/ Don Miguel Eza, nº 2<br />
31500 TUDELA                        </div>
  </div>
  <div class="box-services-2">
    <div class="box-left"><i class="icon icon-4 icon_mobile"></i></div>
    <div class="box-right">
      T.  848 421 991            </div>
  </div>
  <div class="box-services-2">
    <div class="box-left"><i class="icon icon-4 icon_clock_alt"></i></div>
    <div class="box-right">
                      Lunes y miércoles de 8:00h. a 13:30h.<br />
Martes y jueves de 8:00h. a 20:00h.<br />
Viernes cerrado                  </div>
  </div>
</div>
<script type="text/javascript">
function initMap(){
  var center = {lat: 42,0607974, lng: -1,6051186};
  var map = new google.maps.Map(document.getElementById( 'simplemap-11436'), {
    zoom: 18,
    center: center
  });
}
</script>
"""

# Same template, Pamplona's spot: a two-line address and hours.
NAVARRA_CONTACT_PAMPLONA_HTML = """
<div class="block block-contact">
  <div class="box-services-2">
    <div class="box-left"><i class="icon icon-4 icon_pin_alt"></i></div>
    <div class="box-right">
      C/ Irunlarrea, 3 (Hospital de Navarra)<br />
      31008 PAMPLONA
    </div>
  </div>
  <div class="box-services-2">
    <div class="box-left"><i class="icon icon-4 icon_mobile"></i></div>
    <div class="box-right">
      T. 848 422 500
    </div>
  </div>
  <div class="box-services-2">
    <div class="box-left"><i class="icon icon-4 icon_clock_alt"></i></div>
    <div class="box-right">
      De lunes a jueves de 8:00h. a 20:00h.<br />
      Viernes de 8:00h. a 14:30h.
    </div>
  </div>
</div>
<script type="text/javascript">
function initMap(){
  var center = {lat: 42,804981957138, lng: -1,6653321776321};
}
</script>
"""

# Trimmed from the calendar's JSON feed (.../adona/calendars/get.json): a
# stop with a dotted time, a stop from before today, the empty placeholder
# entry, and a stop whose venue is on a second line.
NAVARRA_CALENDAR_EVENTS = {
    "events": [
        {
            "id": 1,
            "title": "SANTACARA 16:45 - 20:45\nCentro de Salud",
            "start": "2026-10-27",
            "end": "2026-10-27",
        },
        {
            "id": 2,
            "title": "LUMBIER 16:45 - 21:00\nCentro Cívico",
            "start": "2026-10-28",
            "end": "2026-10-28",
        },
        {
            "id": 3,
            "title": "LOS ARCOS 17.00 - 21.00\nCasa de la Villa",
            "start": "2026-10-29",
            "end": "2026-10-29",
        },
        {"id": 4, "title": ".  - \n", "start": "2026-10-30", "end": "2026-10-30"},
    ]
}

# Trimmed from https://www.bancosangrerioja.org/donacion/donde-donar-sangre —
# the Banco's map legend and its marker's coordinates (the page's own script).
LA_RIOJA_FIXED_POINT_HTML = """
<html><body>
<script>
    function initMap() {
            var myLatLngBS = {lat: 42.451333, lng: -2.427574};
            mapBS = new google.maps.Map(document.getElementById('mapBS'), {
                center: {lat: 42.451333, lng: -2.427574},
                zoom: 16
            });
    }
</script>
<div id="mapBS"></div>
<div id="leyendaMapaBS">
    <strong><i class="fa fa-tint" aria-hidden="true"></i> Banco de Sangre del Hospital San Pedro</strong><br />
    Horario:
    De lunes a viernes de 8 a 20 horas
    Sábados de 9 a 14 horas<br />
</div>
</body></html>
"""

# Trimmed from https://www.bancosangrerioja.org/ — the "Estado de las reservas"
# blood-bag grid, one image per blood type, plus the legend under it.
LA_RIOJA_HOME_HTML = """
<html><body>
<div class="estadosReservas">
    <div class="row">
    <div class="col"><img src="https://www.bancosangrerioja.org/images/estados/estado-0-neg-2.png" /></div>
    <div class="col"><img src="https://www.bancosangrerioja.org/images/estados/estado-0-pos-3.png" /></div>
    <div class="col"><img src="https://www.bancosangrerioja.org/images/estados/estado-A-neg-1.png" /></div>
    <div class="col"><img src="https://www.bancosangrerioja.org/images/estados/estado-A-pos-1.png" /></div>
     </div>
    <div class="row">
    <div class="col"><img src="https://www.bancosangrerioja.org/images/estados/estado-B-neg-2.png" /></div>
    <div class="col"><img src="https://www.bancosangrerioja.org/images/estados/estado-B-pos-2.png" /></div>
    <div class="col"><img src="https://www.bancosangrerioja.org/images/estados/estado-AB-neg-2.png" /></div>
    <div class="col"><img src="https://www.bancosangrerioja.org/images/estados/estado-AB-pos-3.png" /></div>
     </div>
</div>
<div class="row estadosReservasLeyenda">
    <div class="col">
        <img src="https://www.bancosangrerioja.org/images/estados/estado-1.png" /> <small>Dona hoy</small>
    </div>
    <div class="col">
        <img src="https://www.bancosangrerioja.org/images/estados/estado-2.png" /> <small>Dona en 2 ó 3 días</small>
    </div>
    <div class="col">
        <img src="https://www.bancosangrerioja.org/images/estados/estado-3.png" /> <small>Dona en tu próxima colecta</small>
    </div>
</div>
</body></html>
"""

# Trimmed from .../calendario-extracciones?f=10-2026 — the month grid's
# "#calCuerpo" cells. Day 1 is in the past (dropped when today is the 28th),
# the 28th has two stops, and an empty cell has no day number.
LA_RIOJA_CALENDAR_HTML = """
<html><body>
<div id="calCuerpo">
    <div class="row hidden-xs">
        <div class="col">Lunes</div>
        <div class="col">Martes</div>
    </div>
    <div class="row">
        <div class="col"><span class="visually-hidden"> deOctubre 2026</span>
        </div>
        <div class="col">1<span class="visually-hidden"> deOctubre 2026</span>
                    <a href="https://www.bancosangrerioja.org/el-banco-de-sangre/calendario-extracciones/colecta?c=4992">
                        <i class="fa fa-tint" aria-hidden="true"></i> <strong>Logroño - S. Millán.</strong>10:00 -13:45
                        <br />Calle San Millán 20  <br />
                    </a>
        </div>
    </div>
    <div class="row">
        <div class="col">28<span class="visually-hidden"> deOctubre 2026</span>
                    <a href="https://www.bancosangrerioja.org/el-banco-de-sangre/calendario-extracciones/colecta?c=5013">
                        <i class="fa fa-tint" aria-hidden="true"></i> <strong>Logroño - Cosme García</strong>09:30 -13:45
                        <br />Ies Cosme García  <br />
                    </a>
                    <a href="https://www.bancosangrerioja.org/el-banco-de-sangre/calendario-extracciones/colecta?c=5014">
                        <i class="fa fa-tint" aria-hidden="true"></i> <strong>Rincón de Soto</strong>17:30 -21:00
                        <br />Avda. La Rioja, parada de autobús<br />
                    </a>
        </div>
        <div class="col">29<span class="visually-hidden"> deOctubre 2026</span>
                    <a href="https://www.bancosangrerioja.org/el-banco-de-sangre/calendario-extracciones/colecta?c=5038">
                        <i class="fa fa-tint" aria-hidden="true"></i> <strong>UNIR. Universidad Internacional de La Rioja. Avda. de la Paz,137</strong>17:30 -21:00
                        <br />Logroño<br />
                    </a>
        </div>
    </div>
</div>
</body></html>
"""

# Trimmed from .../calendario-extracciones/colecta?c=5013 — the stop's own
# detail page, whose embedded map carries its exact coordinates.
LA_RIOJA_STOP_MAP_HTML = """
<html><body>
<div class="col-sm-6">
<iframe class='embedGoogleMap' width='568' height='489' style='border: 0px solid #000000' src='https://www.google.com/maps?q=42.455000000000000%2C-2.451745000000000&z=14&t=m&output=embed'></iframe>
</div>
</body></html>
"""

# The same page for a stop whose map has no coordinates (the source writes
# "q=%2C" for it), which falls back to geocoding.
LA_RIOJA_STOP_NO_MAP_HTML = """
<html><body>
<div class="col-sm-6">
<iframe class='embedGoogleMap' width='568' height='489' style='border: 0px solid #000000' src='https://www.google.com/maps?q=%2C&z=14&t=m&output=embed'></iframe>
</div>
</body></html>
"""

# Trimmed from https://www.sspa.juntadeandalucia.es/servicioandaluzdesalud/el-sas/servicios-y-centros/informacion-por-centros/16508
# (Centro de transfusión de Sevilla): the centre's own address and weekly
# timetable, plus its "Se puede donar en..." mobile collections. The last
# three rows show the hour formats the source mixes in ("DE 17 A 21 H ( P )",
# "09:30 a 13:30 y 16:30 a 20:30", "DESDE LAS 17,00 HORAS").
ANDALUCIA_CENTER_HTML = """
<html><body>
<h1 class="center-label__title center-label__title--main">
  Centro de transfusión, tejidos y células de Sevilla
</h1>
<div class="center-address__address-postal">
  <div class="field__label">Dirección postal</div>
  <div class="field field--name-field-direccion field__item"><p>Avda. Manuel Siurot, 39</p></div>
  <div class="field field--name-field-codigo-postal field__item">41013</div>
  <div class="field field--name-field-municipio field__item">Sevilla</div>
</div>
<div class="center-address__schedules">
  <table class="center-schedule__table">
    <tbody>
      <tr>
        <td>Lunes</td>
        <td><ul class="center-schedule__list">
          <li class="center-schedule__item">08:30 - 14:30</li>
          <li class="center-schedule__item">15:30 - 21:30</li>
        </ul></td>
      </tr>
      <tr>
        <td>Sábado</td>
        <td><ul class="center-schedule__list">
          <li class="center-schedule__item">09:00 - 15:00</li>
        </ul></td>
      </tr>
    </tbody>
  </table>
</div>
<div class="center-blood">
  <p class="center-blood__title">Se puede donar en...</p>
  <div class="views-element-container">
    <table class="views-table views-view-table cols-5">
      <thead>
        <tr>
          <th>Fecha</th><th>Día</th><th>Localidad</th><th>Lugar</th><th>Hora</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>28-10-2026</td><td>X</td><td>DOS HERMANAS</td>
          <td>HERMANDAD DEL ROCÍO</td><td>17:00 - 21:00</td>
        </tr>
        <tr>
          <td>29-10-2026</td><td>J</td><td>ALCALÁ DE GUADAIRA</td>
          <td>CEIP OROMANA</td><td>DE 17 A 21 H ( P )</td>
        </tr>
        <tr>
          <td>29-10-2026</td><td>J</td><td>CORIA DEL RÍO</td>
          <td>CENTRO DE ESTUDIOS CEPER</td><td>09:30 a 13:30 y 16:30 a 20:30</td>
        </tr>
        <tr>
          <td>30-10-2026</td><td>V</td><td>VILLAMANRIQUE DE LA CONDESA</td>
          <td>BIBLIOTECA</td><td>DESDE LAS 17,00 HORAS</td>
        </tr>
      </tbody>
    </table>
  </div>
</div>
</body></html>
"""


ASTURIAS_FIXED_POINTS_HTML = r"""
<html><body><main id="main" class="site-main"><div class="wpb_text_column"><div class="wpb_wrapper"><h5 align="center"><strong>H.U.C.A. &#8211; CENTRO COMUNITARIO DE SANGRE Y TEJIDOS DE ASTURIAS</strong></h5>
<p style="text-align: center;"><strong style="line-height: 1.5em;">H.U.C.A. Hospitalización &#8211; Planta 0. Av. Roma, S/N, 33011, Oviedo, Asturias</strong></p>
<p style="text-align: center;">Lunes a viernes: 08.30-20.30 h. | Sábados: 10.00-14.00 h.</p>
<p>&nbsp;</p>
<p style="text-align: right;"><img fetchpriority="high" decoding="async" class="alignleft size-full wp-image-25465" src="https://donasturias.org/wp-content/uploads/2026/05/2605-DONAASTURIAS-HUCA-II-570x337.png" alt="2605 DONAASTURIAS - HUCA II" width="374" height="221" /></p>
<p style="text-align: right;"><iframe style="border: 0;" src="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2900.0813436145368!2d-5.829514423865379!3d43.37532317035888!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0xd368d175232031b%3A0xe42481e467f1c6bd!2sCentro%20Comunitario%20de%20Sangre%20y%20Tejidos%20de%20Asturias%20%7C%20Donaasturias%20%7C%20Donaci%C3%B3n%20de%20sangre!5e0!3m2!1ses!2ses!4v1779867063059!5m2!1ses!2ses" width="429" height="208" allowfullscreen="allowfullscreen"></iframe><br />
<small><a style="color: #0000ff; text-align: left;" href="https://maps.google.com/?q=Centro+Comunitario+de+Sangre+y+Tejidos+de+Asturias">Ver mapa más grande</a></small></p>
<h5 align="center"><strong>CENTRO DE SALUD PUERTA DE LA VILLA</strong></h5>
<p style="text-align: center;"><strong style="line-height: 1.5em;">Calle Donato Argüelles, 20, 33206 Gijón, Asturias</strong></p>
<p style="text-align: center;">Lunes y Miércoles: 16.00-21.00 h. |  Viernes: 10.00-20.00 h.</p>
<p>&nbsp;</p>
<p style="text-align: right;"><img decoding="async" class="size-full wp-image-397 alignleft" src="https://www.donasturias.org/wp-content/uploads/2014/02/Oviedo2.jpg" alt="Oviedo2" width="470" height="200" /></p>
<p style="text-align: right;"><iframe loading="lazy" src="https://maps.google.es/maps?f=q&amp;source=s_q&amp;hl=es&amp;geocode=&amp;q=centro+de+salud+cerca+de+Puerta+la+Villa,+Gij%C3%B3n%2FXix%C3%B3n&amp;aq=0&amp;oq=Centro+de+Salud+Puerta+La+Villa&amp;sll=43.540099,-5.66479&amp;sspn=0.009099,0.021007&amp;g=C%2F+Donato+Arg%C3%BCelles,+s%2Fn+33206+GIJON-ASTURIAS&amp;ie=UTF8&amp;hq=centro+de+salud&amp;hnear=Puerta+la+Villa&amp;ll=43.539316,-5.664576&amp;spn=0.018199,0.042014&amp;t=m&amp;z=14&amp;iwloc=A&amp;cid=11235643786092270557&amp;output=embed" width="429" height="208" frameborder="0" marginwidth="0" marginheight="0" scrolling="no"></iframe><br />
<small><a style="color: #0000ff; text-align: left;" href="https://maps.google.es/maps?f=q&amp;source=embed&amp;hl=es&amp;geocode=&amp;q=centro+de+salud+cerca+de+Puerta+la+Villa,+Gij%C3%B3n%2FXix%C3%B3n&amp;aq=0&amp;oq=Centro+de+Salud+Puerta+La+Villa&amp;sll=43.540099,-5.66479&amp;sspn=0.009099,0.021007&amp;g=C%2F+Donato+Arg%C3%BCelles,+s%2Fn+33206+GIJON-ASTURIAS&amp;ie=UTF8&amp;hq=centro+de+salud&amp;hnear=Puerta+la+Villa&amp;ll=43.539316,-5.664576&amp;spn=0.018199,0.042014&amp;t=m&amp;z=14&amp;iwloc=A&amp;cid=11235643786092270557">Ver mapa más grande</a></small></p>
<h5 align="center"><strong>CRUZ ROJA DE GIJÓN</strong></h5>
<p style="text-align: center;"><strong>C/ Uría nº 37, 33202 Gijón, Asturias ‎</strong></p>
<p style="text-align: center;">Lunes, Miércoles y Viernes:  11.00-14.00 h.</p>
<p>&nbsp;</p>
<p style="text-align: right;"><img loading="lazy" decoding="async" class="size-full wp-image-406 alignleft" src="https://www.donasturias.org/wp-content/uploads/2014/02/cruzroja.jpg" alt="cruzroja" width="441" height="200" /></p>
<p style="text-align: right;"><iframe loading="lazy" src="https://maps.google.es/maps?f=q&amp;source=s_q&amp;hl=es&amp;geocode=&amp;q=Cruz+Roja,+Gij%C3%B3n%2FXix%C3%B3n&amp;aq=0&amp;oq=cr&amp;sll=43.539854,-5.655105&amp;sspn=0.009099,0.021007&amp;g=43.53892,-5.655001&amp;ie=UTF8&amp;hq=&amp;hnear=Cruz+Roja&amp;ll=43.539854,-5.655105&amp;spn=0.009099,0.021007&amp;t=m&amp;z=14&amp;iwloc=A&amp;output=embed" width="438" height="202" frameborder="0" marginwidth="0" marginheight="0" scrolling="no"></iframe><br />
<small><a style="color: #0000ff; text-align: left;" href="https://maps.google.es/maps?f=q&amp;source=embed&amp;hl=es&amp;geocode=&amp;q=Cruz+Roja,+Gij%C3%B3n%2FXix%C3%B3n&amp;aq=0&amp;oq=cr&amp;sll=43.539854,-5.655105&amp;sspn=0.009099,0.021007&amp;g=43.53892,-5.655001&amp;ie=UTF8&amp;hq=&amp;hnear=Cruz+Roja&amp;ll=43.539854,-5.655105&amp;spn=0.009099,0.021007&amp;t=m&amp;z=14&amp;iwloc=A">Ver mapa más grande</a></small></p>
<h5 align="center"><strong>ASOCIACIÓN DE DONANTES DE SANGRE DE AVILÉS</strong></h5>
<p style="text-align: center;"><strong>Plaza Santiago López, 1, 33402 Avilés, Asturias</strong></p>
<p style="text-align: center;">Martes y jueves: 16.00-21.00 h.</p>
<p style="text-align: center;">Primer jueves laborable de cada mes: 9.00-14.00 y 16.00-21.00 h.</p>
<p>&nbsp;</p>
<p style="text-align: right;"><img loading="lazy" decoding="async" class="size-full wp-image-410 alignleft" src="https://www.donasturias.org/wp-content/uploads/2014/02/aviless.jpg" alt="aviless" width="441" height="200" /></p>
<p style="text-align: right;"><iframe loading="lazy" src="https://maps.google.es/maps?f=q&amp;source=s_q&amp;hl=es&amp;geocode=&amp;q=donantes+de+sangre+aviles&amp;aq=&amp;sll=43.539854,-5.655212&amp;sspn=0.009099,0.021007&amp;ie=UTF8&amp;hq=&amp;hnear=&amp;ll=43.555626,-5.919465&amp;spn=0.006295,0.006295&amp;t=m&amp;iwloc=A&amp;output=embed" width="440" height="194" frameborder="0" marginwidth="0" marginheight="0" scrolling="no"></iframe><br />
<small><a style="color: #0000ff; text-align: left;" href="https://maps.google.es/maps?f=q&amp;source=embed&amp;hl=es&amp;geocode=&amp;q=donantes+de+sangre+aviles&amp;aq=&amp;sll=43.539854,-5.655212&amp;sspn=0.009099,0.021007&amp;ie=UTF8&amp;hq=&amp;hnear=&amp;ll=43.555626,-5.919465&amp;spn=0.006295,0.006295&amp;t=m&amp;iwloc=A">Ver mapa más grande</a></small></p></div></div></main></body></html>
"""

ASTURIAS_HOME_HTML = r"""
<html><body><img fetchpriority="high" decoding="async" src="//donasturias.org/wp-content/uploads/2026/10/DONAASTURIAS-Slider-Dona-Sangre-Temporada.png" alt="DONAASTURIAS Slider - Dona Sangre - Temporada" title="DONAASTURIAS Slider &#8211; Dona Sangre &#8211; Temporada" width="1920" height="850" class="rev-slidebg tp-rs-img" data-bg="p:center top;" data-no-retina><h2 class="vc_custom_heading">Estado de las reservas de hematíes</h2><div class="wpb_single_image"><img loading="lazy" decoding="async" data-vc-zoom="https://donasturias.org/wp-content/uploads/2023/08/omas230-1.jpg" width="109" height="108" src="https://donasturias.org/wp-content/uploads/2023/08/omas230-1.jpg" class="vc_single_image-img attachment-full" alt="" /><img loading="lazy" decoding="async" width="109" height="108" src="https://donasturias.org/wp-content/uploads/2024/07/o-90.jpg" class="vc_single_image-img attachment-full" alt="" /><img loading="lazy" decoding="async" width="109" height="108" src="https://donasturias.org/wp-content/uploads/2022/12/Amas140.jpg" class="vc_single_image-img attachment-full" alt="" /><img loading="lazy" decoding="async" width="109" height="108" src="https://donasturias.org/wp-content/uploads/2022/09/A-45.jpg" class="vc_single_image-img attachment-full" alt="" /><img loading="lazy" decoding="async" width="109" height="108" src="https://donasturias.org/wp-content/uploads/2023/07/Bmas60.jpg" class="vc_single_image-img attachment-full" alt="" /><img loading="lazy" decoding="async" width="109" height="108" src="https://donasturias.org/wp-content/uploads/2024/04/B-9.jpg" class="vc_single_image-img attachment-full" alt="" /><img loading="lazy" decoding="async" width="109" height="108" src="https://donasturias.org/wp-content/uploads/2025/05/ABmas40.jpg" class="vc_single_image-img attachment-full" alt="" /><img loading="lazy" decoding="async" width="109" height="108" src="https://donasturias.org/wp-content/uploads/2023/07/ab-1.jpg" class="vc_single_image-img attachment-full" alt="" /></div></body></html>
"""

ASTURIAS_EVENTS_JSON = r"""
{
 "events": [
  {
   "id": 26727,
   "title": "Acuartelamiento Cabo Noval",
   "start_date": "2026-10-28 00:00:00",
   "end_date": "2026-10-28 23:59:59",
   "url": "https://donasturias.org/eventos/acuartelamiento-cabo-noval-3/",
   "description": "<p>09.00-14.00 | Delante del botiquín.</p>"
  },
  {
   "id": 26729,
   "title": "Carbayín",
   "start_date": "2026-10-28 00:00:00",
   "end_date": "2026-10-28 23:59:59",
   "url": "https://donasturias.org/eventos/carbayin-2/",
   "description": "<p>16.00-17.30 | <strong>Carbayín Bajo</strong>. Bar Pepín.</p>\n<p>18.00-21.00 | <strong>Carbayín Alto.</strong> Plaza de la Iglesia.</p>"
  },
  {
   "id": 26733,
   "title": "Oviedo",
   "start_date": "2026-10-28 00:00:00",
   "end_date": "2026-10-28 23:59:59",
   "url": "https://donasturias.org/eventos/oviedo-33/",
   "description": "<p>09.00-15.00 y 15.00-21.00 | <strong>San Lázaro.</strong> C/ San Lázaro, 2.</p>"
  },
  {
   "id": 26784,
   "title": "PUNTOS FIJOS",
   "start_date": "2026-10-28 00:00:00",
   "end_date": "2026-10-28 23:59:59",
   "url": "https://donasturias.org/eventos/puntos-fijos-83/",
   "description": "<p>08.30-20.30 | <strong>HUCA · C.C. Sangre y Tejidos de Asturias. </strong>Entrada hospitalización.</p>\n<p>11.00-14.00 | <strong>Gijón. Cruz Roja</strong>. C/ Uría, 37.</p>\n<p>16.00-21.00 | <strong>Gijón. C.S. Puerta de la Villa</strong>. 1º Planta. C/ Donato Argüelles, 20.</p>"
  },
  {
   "id": 26735,
   "title": "Acuartelamiento Cabo Noval",
   "start_date": "2026-10-29 00:00:00",
   "end_date": "2026-10-29 23:59:59",
   "url": "https://donasturias.org/eventos/acuartelamiento-cabo-noval-4/",
   "description": "<p>09.00-14.00 | Delante del botiquín.</p>"
  },
  {
   "id": 26745,
   "title": "UNIOVI | Campus Llamaquique",
   "start_date": "2026-10-29 00:00:00",
   "end_date": "2026-10-29 23:59:59",
   "url": "https://donasturias.org/eventos/uniovi-campus-llamaquique/",
   "description": "<p>08.30-14.30 y 14.30-20.30 | C/ Aniceto Sela.</p>"
  },
  {
   "id": 26796,
   "title": "PUNTOS FIJOS",
   "start_date": "2026-10-29 00:00:00",
   "end_date": "2026-10-29 23:59:59",
   "url": "https://donasturias.org/eventos/puntos-fijos-88/",
   "description": "<p>08.30-20.30 |<strong> HUCA · C.C. Sangre y Tejidos de Asturias. </strong>Entrada hospitalización.</p>\n<p>16.00-21.00 | <strong>Avilés · Asociación de Donantes de Sangre.</strong> Plaza Santiago López, 1-Bajo.</p>"
  },
  {
   "id": 26751,
   "title": "Oviedo",
   "start_date": "2026-10-30 00:00:00",
   "end_date": "2026-10-30 23:59:59",
   "url": "https://donasturias.org/eventos/oviedo-34/",
   "description": "<p>15.00-21.00 | <strong>Ventanielles</strong>. Plaza de la Iglesia (Pza. Lago Enol).</p>"
  },
  {
   "id": 26753,
   "title": "Arcelor Mittal Avilés",
   "start_date": "2026-10-30 00:00:00",
   "end_date": "2026-10-30 23:59:59",
   "url": "https://donasturias.org/eventos/arcelor-mittal-aviles-2/",
   "description": "<p>09.00-11.30 | Centro Desarrollo Tecnológico.</p>"
  },
  {
   "id": 26607,
   "title": "Gijón",
   "start_date": "2026-10-01 00:00:00",
   "end_date": "2026-10-01 23:59:59",
   "url": "https://donasturias.org/eventos/gijon-27/",
   "description": "<p>09.00-14.00 y 16.00-21.00 | <strong>La Arena.</strong> C/ Menéndez Pelayo, entre núm. 13 y 17.</p>\n<p>09.00-14.00 y 16.00-21.00 | <strong>Natahoyo.</strong> C/ El Cortijo, delante AAVV Atalía, al lado del parque.</p>"
  }
 ]
}
"""
