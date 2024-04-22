# Puntos de Donación de Sangre de la Comunidad de Madrid

## [El Mapa](https://arredond.github.io/hirudo/)

## El _qué_

Este es un pequeño proyecto para extraer automáticamente los puntos de donación de sangre
fijos y móviles de la Comunidad de Madrid y plasmarlos en un mapa, junto con otra información
de interés.

## El _porqué_

Si quieres donar sangre en la Comunidad de Madrid, lo más probable es que hayas acudido a
[esta página web](https://www.comunidad.madrid/servicios/salud/donacion-sangre). Aunque ha
mejorado con los años, hay una cosa que no cambia: _las listas_.

Si quieres encontrar dónde puedes donar, acabarás deambulando por listas de
[puntos fijos](http://donarsangre.sanidadmadrid.org/fijos.aspx) y
[puntos móviles](http://donarsangre.sanidadmadrid.org/moviles.aspx) con direcciones, fechas
y horarios.

Entrando en la tercera década del siglo XXI, nos vamos mereciendo un mapa.

## El _cómo_

Usamos [Supabase](https://supabase.io/) como _backend_ y [Leaflet](https://leafletjs.com/)
para el _front_, además de un poco de código en Python para extraer los datos y un
Geocoder (Google) para convertir las direcciones en coordenadas. No tiene mucho más.

## Peticiones / ruegos / dudas

Simplemente abre [un _issue_](https://github.com/arredond/hirudo/issues/new) e intentaré
atenderte lo antes posible.
