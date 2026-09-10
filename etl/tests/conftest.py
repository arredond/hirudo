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
