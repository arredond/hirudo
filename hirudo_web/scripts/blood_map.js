// add map variable
export const map = L.map('map', {
    zoomControl: true,
    center: [40.4, -3.7],
    zoom: 10
});

const fixedPointLayer = new L.LayerGroup();
const mobilePointLayer = new L.LayerGroup();

// Custom tent icon
// TO DO: Attribute the designer
// <div>Icons made by <a href="https://www.freepik.com" title="Freepik">Freepik</a> from <a href="https://www.flaticon.com/" title="Flaticon">www.flaticon.com</a></div>
const puntosFijosIcon = L.icon({
    iconUrl: './dist/blooddrop.png',
    iconSize: [25, 25],
    iconAnchor: [12.5, 12.5],
    popupAnchor: [1, -34]
});

const puntosMovilesIcon = L.icon({
    iconUrl: './dist/directions_bus_filled.svg',
    iconSize: [25, 25],
    iconAnchor: [12.5, 12.5],
    popupAnchor: [1, -34]
});

export function setupMap() {
    // Add markers layer
    fixedPointLayer.addTo(map);
    mobilePointLayer.addTo(map);
    
    // add Voyager Basemap as default but allow usage of Google Maps
    let cartoBasemap = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png', {
        maxZoom: 18,
        attribution: '&copy;<a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, &copy;<a href="https://carto.com/attribution">CARTO</a>'
    }).addTo(map);

    // keep Google Satellite map for high zoom levels - with labels too
    let googleBasemap = L.tileLayer('https://mt1.google.com/vt/lyrs=r&x={x}&y={y}&z={z}', {
        maxZoom: 18
    })

    L.control.layers(
        {
            'CARTO Voyager': cartoBasemap,
            'Google Maps': googleBasemap
        }
    ).addTo(map);
    L.control.locate().addTo(map);

    // Custom control with image
    // Kudos to https://stackoverflow.com/questions/46002113/javascript-reactjs-display-image-with-readablestream-as-source
    const url_niveles_reserva = 'https://www.comunidad.madrid/sites/default/files/styles/imagen_enlace_opcional/public/doc/sanidad/info/niveles_de_reserva_sangre_0.jpg'

    fetch(url_niveles_reserva)
        .then(response => response.blob())
        .then(blob => {
            console.log(blob);
            L.Control.Watermark = L.Control.extend({
                onAdd: function (map) {
                    var img = L.DomUtil.create('img');

                    img.src = URL.createObjectURL(blob);
                    img.style.width = '300px';

                    return img;
                },

                onRemove: function (map) {
                    // Nothing to do here
                }
            });

            L.control.watermark = function (opts) {
                return new L.Control.Watermark(opts);
            }

            L.control.watermark({position: 'bottomleft'}).addTo(map);
        })
        .catch(err => console.log(err))

}

export function addBloodPoints(bloodPoints, isFixedPoint) {

    // Wrapper function for layer popups
    function removeEmpty(obj) {
        return Object.fromEntries(Object.entries(obj).filter(([_, v]) => v != null));
    }

    function tablePopup(feature, layer, keyRename) {
        const name_field = 'nombre';
        let tableElements = []
        for (const [key, value] of Object.entries(removeEmpty(feature.properties))) {
            if ([name_field, 'url'].includes(key)) {
                continue
            }
            tableElements.push(`<tr><td><strong>${keyRename[key]}</strong></td><td>${value}</td></tr>`)
        }
        const table = `<table>
                        <thead>
                            <tr>
                                <th colspan="2"><h2>${feature.properties[name_field]}</h2></th>
                            </tr>
                        </thead>
                        <tbody>
                        ${tableElements.join('')}
                        </tbody>
                    </table>
                    <img src="./dist/gmaps.png" alt="Link a Google Maps" width="10"><a href="${feature.properties.url}">    Ver en Google Maps</a>
                    `
        layer.bindPopup(table);
    }

    function addPointToMap(bloodPoint) {
        const keys = bloodPoints.keys.reduce((a, v) => ({...a, [v['db']]: v['original']}), {})

        function fijosTablePopup(feature, layer) {
            return tablePopup(feature, layer, keys)
        }

        let layer = L.geoJSON(bloodPoint, {
            pointToLayer: function (feature, latlng) {
                return L.marker(latlng, {icon: isFixedPoint ? puntosFijosIcon : puntosMovilesIcon});
            },
            onEachFeature: fijosTablePopup
        });
        if (isFixedPoint) {
            fixedPointLayer.addLayer(layer);
        } else {
            mobilePointLayer.addLayer(layer);
        }
    }
    if (bloodPoints.features) {
        for (const bloodPoint of bloodPoints.features) {
            addPointToMap(bloodPoint)
        }   
    }
}

export function clearMarkers() {
    mobilePointLayer.clearLayers();
}
