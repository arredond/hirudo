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
