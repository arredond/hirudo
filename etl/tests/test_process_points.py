"""Tests for process_fixed_points / process_mobile_points — region stamping.

These mock every I/O boundary (scraping, geocoding, DB) and only check that
each uploaded frame carries the region column for both regions.
"""

import geopandas as gpd
import pandas as pd

import main

NO_LOCATION_OVERRIDES = pd.DataFrame(
    columns=["match", "lugar", "latitude", "longitude"]
)


def test_process_fixed_points_stamps_region(mocker):
    manual_points = pd.DataFrame(
        {"name": ["Manual Center"], "latitude": [40.4], "longitude": [-3.7]}
    )
    other_donations = pd.DataFrame({"name": ["Manual Center"], "plasma": ["yes"]})
    scraped_madrid = pd.DataFrame(
        {"name": ["Hospital X"], "latitude": [40.5], "longitude": [-3.6]}
    )
    scraped_cyl = pd.DataFrame(
        {
            "name": ["Hospital Y"],
            "direccion": ["Calle Y, 1"],
            "gmaps_url": ["https://maps.app.goo.gl/abc"],
            "province": ["avila"],
            "url": ["https://www.centrodehemoterapiacyl.es/puntos-de-donacion/avila/"],
            "horario": ["Lunes a viernes: 9:00 a 14:00"],
            "latitude": [40.6],
            "longitude": [-4.7],
        }
    )
    scraped_clm = pd.DataFrame(
        {
            "name": ["ALBACETE"],
            "localidad": ["ALBACETE"],
            "direccion": ["Hospital General Universitario. C/. Hermanos Falcó, 37."],
            "horario": ["Lunes a viernes de 8:30 a 14:00 h."],
            "telefono": ["967 24 30 72"],
            "url": ["https://sanidad.castillalamancha.es/puntos-fijos-de-donacion"],
        }
    )
    scraped_aragon = pd.DataFrame(
        {
            "name": ["Hospital San Jorge"],
            "localidad": ["Huesca"],
            "direccion": ["Martínez de Velasco, 36"],
            "telefono": ["974 247 000"],
            "horario": ["de lunes a jueves de 8:30 h. a 14:00 h."],
            "plasma": [False],
            "url": ["https://bancosangrearagon.org/"],
        }
    )

    scraped_valencia = pd.DataFrame(
        {
            "name": ["Centro de Transfusión de Alicante"],
            "direccion": ["CARRETERA NACIONAL 332, KM. 113"],
            "localidad": ["Sant Joan D Alacant"],
            "codigo_postal": ["03550"],
            "plasma": [True],
            "horario": ["mar 27/10 08:30-21:00"],
            "schedule": [[("27/10/2026", "08:30-21:00")]],
            "url": ["https://centro-transfusion.san.gva.es/es/puntos-de-donacion"],
        }
    )

    scraped_cataluna = pd.DataFrame(
        {
            "name": ["Hospital Clínic"],
            "horario": ["Lunes a viernes a 8.30 a 21 h."],
            "direccion": ["Villarroel, 170"],
            "codigo_postal": ["08036"],
            "localidad": ["Barcelona"],
            "telefono": ["93 227 54 00"],
            "plasma": [True],
            "url": ["https://www.bancsang.net/es/hospitales/3/"],
        }
    )

    scraped_galicia = pd.DataFrame(
        {
            "name": ["Local de doazón de Ourense"],
            "venue": ["Plaza Paz Novoa nº3. Aparcamento gratuíto"],
            "direccion": ["Plaza Paz Novoa nº3. Aparcamento gratuíto · 32003 Ourense"],
            "localidad": ["Ourense"],
            "codigo_postal": ["32003"],
            "horario": ["Luns a venres de 8:00 a 15:00"],
            "latitude": [None],
            "longitude": [None],
            "plasma": [True],
            "url": ["https://ados.sergas.gal/cartafol/ADOS-locais"],
        }
    )

    scraped_la_rioja = pd.DataFrame(
        {
            "name": ["Banco de Sangre del Hospital San Pedro"],
            "localidad": ["Logroño"],
            "direccion": ["Hospital San Pedro"],
            "latitude": [42.451333],
            "longitude": [-2.427574],
            "horario": ["De lunes a viernes de 8 a 20 horas Sábados de 9 a 14 horas"],
            "url": ["https://www.bancosangrerioja.org/donacion/donde-donar-sangre"],
        }
    )

    scraped_pais_vasco = pd.DataFrame(
        {
            "name": ["Ambulatorio Olaguibel (Vitoria-Gasteiz)"],
            "localidad": ["Vitoria-Gasteiz"],
            "direccion": ["OLAGUIBEL, 31"],
            "latitude": [42.846035],
            "longitude": [-2.66569352],
            "schedule": [[("27/10/2026", "08:30-21:00")]],
            "horario": ["mar 27/10 08:30-21:00"],
            "plasma_only": [False],
            "url": ["https://donantesdesangre.eus/donde-donar/"],
        }
    )

    scraped_cantabria = pd.DataFrame(
        {
            "name": [
                "Banco de Sangre y Tejidos del Hospital Universitario Marqués de Valdecilla"
            ],
            "localidad": ["Santander"],
            "direccion": ["Avenida de Valdecilla s/n., Pabellón 13, Planta 0"],
            "telefono": ["942 202 689"],
            "horario": ["lunes a viernes de 8:30 a 21:00h"],
            "gmaps_url": ["https://maps.app.goo.gl/UwoRmWBNeAMJKgKMA"],
            "url": ["https://www.hdsc.org/"],
            "latitude": [43.4564414],
            "longitude": [-3.8280688],
        }
    )

    scraped_navarra = pd.DataFrame(
        {
            "name": ["Banco de Sangre de Tudela"],
            "direccion": ["C/ Don Miguel Eza, nº 2"],
            "localidad": ["Tudela"],
            "telefono": ["848 421 991"],
            "horario": ["Lunes y miércoles de 8:00h. a 13:30h."],
            "latitude": [42.0607974],
            "longitude": [-1.6051186],
            "url": ["https://adona.es/es/contacto-adona/contacto-tudela"],
        }
    )

    scraped_asturias = pd.DataFrame(
        {
            "name": ["Centro de Salud Puerta de la Villa"],
            "direccion": ["Calle Donato Argüelles, 20, 33206 Gijón, Asturias"],
            "localidad": ["Gijón"],
            "codigo_postal": ["33206"],
            "horario": ["Lunes y Miércoles: 16.00-21.00 h. | Viernes: 10.00-20.00 h."],
            "latitude": [43.539316],
            "longitude": [-5.664576],
            "url": ["https://donasturias.org/puntos-fijos/"],
        }
    )

    def fake_geocode_points(df, geocoding_cache, address_column):
        df["longitude"] = -2.0
        df["latitude"] = 39.0
        return df

    mocker.patch("main.pd.read_json", side_effect=[manual_points, other_donations])
    mocker.patch("main.madrid.scrape_fixed_points", return_value=scraped_madrid)
    mocker.patch(
        "main.andalucia.scrape_fixed_points",
        return_value=pd.DataFrame(
            {
                "name": ["Centro de transfusión, tejidos y células de Sevilla"],
                "localidad": ["Sevilla"],
                "direccion": ["Avda. Manuel Siurot, 39, 41013"],
                "horario": ["Lunes 08:00 - 21:00"],
                "schedule": [[("Mo", "08:00 - 21:00")]],
                "provincia": ["Sevilla"],
                "url": ["https://www.sspa.juntadeandalucia.es/"],
            }
        ),
    )
    mocker.patch("main.castilla_y_leon.scrape_fixed_points", return_value=scraped_cyl)
    mocker.patch(
        "main.castilla_la_mancha.scrape_fixed_points", return_value=scraped_clm
    )
    mocker.patch("main.aragon.scrape_fixed_points", return_value=scraped_aragon)
    mocker.patch(
        "main.comunidad_valenciana.scrape_fixed_points", return_value=scraped_valencia
    )
    mocker.patch("main.cataluna.scrape_fixed_points", return_value=scraped_cataluna)
    mocker.patch("main.galicia.scrape_fixed_points", return_value=scraped_galicia)
    mocker.patch("main.la_rioja.scrape_fixed_points", return_value=scraped_la_rioja)
    mocker.patch("main.pais_vasco.scrape_fixed_points", return_value=scraped_pais_vasco)
    mocker.patch("main.cantabria.scrape_fixed_points", return_value=scraped_cantabria)
    mocker.patch("main.navarra.scrape_fixed_points", return_value=scraped_navarra)

    mocker.patch("main.asturias.scrape_fixed_points", return_value=scraped_asturias)
    mocker.patch(
        "main.balears.scrape_fixed_points",
        return_value=pd.DataFrame(
            {
                "name": ["Eivissa"],
                "localidad": ["Eivissa"],
                "direccion": ["Hospital Can Misses. Antiguas Urgencias"],
                "horario": [None],
                "latitude": [38.916526],
                "longitude": [1.418271],
                "url": [
                    "https://www.donasang.org/on-puc-donar/es_punts-fixes/6/eivissa"
                ],
            }
        ),
    )
    mocker.patch("main.refresh_places_cache", side_effect=lambda q, cache, b: cache)
    mocker.patch("main.place_candidate", return_value=None)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)
    mocker.patch("main.open", mocker.mock_open())
    mocker.patch("main.json.load", return_value={})
    mock_to_db = mocker.patch("main.to_db")

    main.process_fixed_points()

    mock_to_db.assert_called_once()
    uploaded, table_name = mock_to_db.call_args.args
    assert table_name == "puntos_fijos"
    assert isinstance(uploaded, gpd.GeoDataFrame)
    assert set(uploaded["region"]) == {
        "Comunidad de Madrid",
        "Andalucía",
        "Castilla y León",
        "Castilla-La Mancha",
        "Aragón",
        "Comunidad Valenciana",
        "Cataluña",
        "Galicia",
        "La Rioja",
        "País Vasco",
        "Cantabria",
        "Comunidad Foral de Navarra",
        "Principado de Asturias",
        "Illes Balears",
    }


def test_scrape_mobile_points_madrid_fixes_known_horario_typo(mocker):
    """Recurring source-site typo: "13.a45" instead of "13:45", which
    otherwise fails opening_hours parsing."""
    scraped = pd.DataFrame(
        {
            "Localidad": ["Madrid"],
            "Lugar": ["C/ Londres (Prr Sgda F)"],
            "Dirección": ["C/ Londres"],
            "Fecha": ["14/09/2026"],
            "Horario": ["10:00 a 13.a45"],
        }
    )

    def fake_geocode(df, geocoding_cache):
        df["longitude"] = -3.7
        df["latitude"] = 40.4
        return df

    mocker.patch("main.madrid.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.geocode_mobile_points", side_effect=fake_geocode)

    df = main.scrape_mobile_points_madrid()

    assert df["horario"].iloc[0] == "10:00 a 13:45"
    assert df["opening_hours"].iloc[0] is not None


def test_scrape_mobile_points_cyl_builds_poi_and_street_candidates(mocker):
    scraped = pd.DataFrame(
        {
            "campana": ["EL CORTE INGLÉS", None],
            "fecha": ["14/09/2026", "18/09/2026"],
            "ubicacion": ["Autobús de Donación", "Autobús de Donación"],
            "horario": ["De 08:45 a 14:15", "De 08:45 a 14:15"],
            "direccion": [
                "Av. María Auxiliadora 71-85 Salamanca (SALAMANCA)",
                "Av. María Auxiliadora 71-85 Salamanca (SALAMANCA)",
            ],
            "province": ["salamanca", "salamanca"],
        }
    )

    captured = {}

    def fake_geocode_points(df, geocoding_cache, address_columns):
        captured["address_columns"] = address_columns
        captured["df"] = df.copy()
        df["longitude"] = -5.66
        df["latitude"] = 40.97
        return df

    mocker.patch("main.castilla_y_leon.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)

    main.scrape_mobile_points_cyl()

    assert captured["address_columns"] == ["address_direccion", "address_campana"]
    seen = captured["df"]
    assert seen["address_campana"].iloc[0] == (
        "EL CORTE INGLÉS, Salamanca, Castilla y León, Spain"
    )
    # No campana on the second (continuation) row -> no POI candidate
    assert pd.isna(seen["address_campana"].iloc[1])
    assert seen["address_direccion"].iloc[0] == (
        "Av. María Auxiliadora 71-85 Salamanca (SALAMANCA), Castilla y León, Spain"
    )


def test_scrape_mobile_points_clm_sets_donation_type_flags(mocker):
    """A "(SÓLO PLASMA)" stop must end up sangre: False — it genuinely
    doesn't take whole blood, unlike every other scraped mobile point."""
    scraped = pd.DataFrame(
        {
            "Día": ["Lunes, 14 Septiembre, 2026", "Lunes, 14 Septiembre, 2026"],
            "Horario": ["17:00-20:30", "16:00-20:00"],
            "Localidad": ["CONSUEGRA", "CEDILLO DEL CONDADO"],
            "Lugar de la Colecta": [
                "Centro de Salud",
                "(SÓLO PLASMA) Consultorio Médico",
            ],
            "Tipo de donación": ["SANGRE", "PLASMA"],
            "province": ["toledo", "toledo"],
        }
    )

    def fake_geocode_points(df, geocoding_cache, address_column):
        df["longitude"] = -4.0
        df["latitude"] = 39.8
        return df

    mocker.patch("main.castilla_la_mancha.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)

    df = main.scrape_mobile_points_clm()

    assert df["plasma"].tolist() == [False, True]
    assert df["sangre"].tolist() == [True, False]
    assert df["medula"].tolist() == [False, False]


def test_process_mobile_points_stamps_region_and_keeps_it_in_output(mocker):
    scraped_madrid = pd.DataFrame(
        {
            "Localidad": ["Madrid"],
            "Lugar": ["Plaza Mayor"],
            "Dirección": ["Calle Mayor 1"],
            "Fecha": ["2026-09-15"],
            "Horario": ["10:00-14:00"],
        }
    )
    scraped_cyl = pd.DataFrame(
        {
            "campana": ["EL BARCO DE ÁVILA"],
            "fecha": ["16/09/2026"],
            "ubicacion": ["Centro de Salud"],
            "horario": ["De 16:45 a 20:15"],
            "direccion": ["C/ Eras s/n El Barco de Avila (AVILA)"],
            "province": ["avila"],
        }
    )
    scraped_clm = pd.DataFrame(
        {
            "Día": ["Lunes, 14 Septiembre, 2026"],
            "Horario": ["17:00-20:30"],
            "Localidad": ["CONSUEGRA"],
            "Lugar de la Colecta": ["Centro de Salud"],
            "Tipo de donación": ["SANGRE"],
            "province": ["toledo"],
        }
    )
    scraped_aragon = pd.DataFrame(
        {
            "title": ["Sariñena, en el Centro de Salud"],
            "who": ["Sariñena"],
            "venue": ["Centro de Salud"],
            "fecha": ["28/10/2026"],
            "horario": ["17:30 a 21:00"],
            "url": ["https://bancosangrearagon.org/extraccion/sarinena/"],
        }
    )

    scraped_valencia = pd.DataFrame(
        {
            "fecha": ["27/10/2026"],
            "poblacion": ["CABANES"],
            "ubicacion": ["CABANES-CASAL JOVE LOCAL, CARRER DELEGADO VALERA, N. 50"],
            "horario": ["16:30-20:30"],
            "province": ["castellon"],
            "venue": ["CASAL JOVE LOCAL"],
            "direccion": ["CARRER DELEGADO VALERA, N. 50"],
            "restriction": [None],
            "plasma_only": [False],
        }
    )

    scraped_cataluna = pd.DataFrame(
        {
            "localidad": ["Gavà"],
            "venue": ["Unidad móvil"],
            "direccion": ["Pl. Jaume Balmes"],
            "fecha": ["28/10/2026"],
            "sangre": [True],
            "plasma": [False],
            "url": ["https://www.bancsang.net/es/donaciones/sangre/recogida/x/"],
            "horario": ["De 17:00 a 21:00"],
        }
    )

    scraped_galicia = pd.DataFrame(
        {
            "area": ["ÁREA SANITARIA A CORUÑA E CEE"],
            "fecha": ["23/10/2026"],
            "concello": ["Sada"],
            "lugar": ["SADA"],
            "direccion": ["UNIDADE MÓBIL DIANTE DA CASA DA XUVENTUDE"],
            "place_text": ["CASA DA XUVENTUDE"],
            "horario": ["09:45 a 14:30 e 15:45 a 21:00"],
            "provisional": [False],
            "url": ["https://ados.sergas.gal/cartafol/proximos-desprazamentos"],
        }
    )

    scraped_la_rioja = pd.DataFrame(
        {
            "lugar": ["Logroño - Cosme García"],
            "localidad": ["Logroño"],
            "direccion": ["Ies Cosme García"],
            "fecha": ["28/10/2026"],
            "horario": ["09:30-13:45"],
            "url": ["https://www.bancosangrerioja.org/colecta?c=5013"],
            "latitude": [42.455],
            "longitude": [-2.451745],
        }
    )

    scraped_pais_vasco = pd.DataFrame(
        {
            "province": ["Bizkaia"],
            "localidad": ["Bilbao"],
            "lugar": ["Bilbao Bombero Etxaniz - Solo Plasma/Cita"],
            "direccion": ["Plaza Bombero Etxaniz 1"],
            "latitude": [43.2584],
            "longitude": [-2.9398],
            "fecha": ["27/10/2026"],
            "horario": ["08:30-13:00, 14:00-18:30"],
            "plasma_only": [True],
            "url": ["https://donantesdesangre.eus/donde-donar/"],
        }
    )

    scraped_navarra = pd.DataFrame(
        {
            "localidad": ["Lumbier"],
            "lugar": ["Centro Cívico"],
            "fecha": ["28/10/2026"],
            "horario": ["16:45 a 21:00"],
            "url": ["https://adona.es/es/calendario-unidad-movil"],
        }
    )

    scraped_asturias = pd.DataFrame(
        {
            "localidad": ["Gijón"],
            "lugar": ["La Arena"],
            "direccion": ["La Arena. C/ Menéndez Pelayo, entre núm. 13 y 17."],
            "fecha": ["01/10/2026"],
            "horario": ["09:00 a 14:00, 16:00 a 21:00"],
            "url": ["https://donasturias.org/eventos/gijon-27/"],
        }
    )

    def fake_geocode_mobile(df, geocoding_cache):
        df["longitude"] = -3.7
        df["latitude"] = 40.4
        return df

    def fake_geocode_points(df, geocoding_cache, address_column):
        df["longitude"] = -4.7
        df["latitude"] = 40.6
        return df

    mocker.patch("main.madrid.scrape_mobile_points", return_value=scraped_madrid)
    mocker.patch(
        "main.andalucia.scrape_mobile_points",
        return_value=pd.DataFrame(
            {
                "fecha": ["28/10/2026"],
                "localidad": ["Dos Hermanas"],
                "lugar": ["HERMANDAD DEL ROCÍO"],
                "horario": ["17:00 - 21:00"],
                "url": ["https://www.sspa.juntadeandalucia.es/"],
                "plasma_only": [False],
            }
        ),
    )
    mocker.patch("main.castilla_y_leon.scrape_mobile_points", return_value=scraped_cyl)
    mocker.patch(
        "main.castilla_la_mancha.scrape_mobile_points", return_value=scraped_clm
    )
    mocker.patch("main.aragon.scrape_mobile_points", return_value=scraped_aragon)
    mocker.patch(
        "main.comunidad_valenciana.scrape_mobile_points",
        return_value=scraped_valencia,
    )
    mocker.patch("main.cataluna.scrape_mobile_points", return_value=scraped_cataluna)
    mocker.patch("main.galicia.scrape_mobile_points", return_value=scraped_galicia)
    mocker.patch("main.la_rioja.scrape_mobile_points", return_value=scraped_la_rioja)
    mocker.patch(
        "main.pais_vasco.scrape_mobile_points", return_value=scraped_pais_vasco
    )
    mocker.patch("main.navarra.scrape_mobile_points", return_value=scraped_navarra)

    mocker.patch("main.asturias.scrape_mobile_points", return_value=scraped_asturias)
    mocker.patch(
        "main.balears.scrape_mobile_points",
        return_value=pd.DataFrame(
            {
                "lugar": ["Banc de Sang i Teixits"],
                "localidad": ["Palma"],
                "direccion": ["Rosselló i Caçador, 20"],
                "fecha": ["28/10/2026"],
                "horario": ["08:00-20:30"],
                "url": [
                    "https://www.donasang.org/on-puc-donar/es_calendari/46968/palma"
                ],
                "aferesis": [False],
                "latitude": [39.582059],
                "longitude": [2.653558],
            }
        ),
    )
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.refresh_places_cache", return_value=pd.DataFrame())
    mocker.patch("main.place_candidate", return_value=None)
    mocker.patch("main.pd.read_json", return_value=NO_LOCATION_OVERRIDES)
    mocker.patch("main.geocode_mobile_points", side_effect=fake_geocode_mobile)
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)
    mock_to_db = mocker.patch("main.to_db")

    main.process_mobile_points()

    mock_to_db.assert_called_once()
    uploaded, table_name = mock_to_db.call_args.args
    assert table_name == "puntos_moviles"
    # region survives the explicit output_cols projection
    assert "region" in uploaded.columns
    assert set(uploaded["region"]) == {
        "Comunidad de Madrid",
        "Andalucía",
        "Castilla y León",
        "Castilla-La Mancha",
        "Aragón",
        "Comunidad Valenciana",
        "Cataluña",
        "Galicia",
        "La Rioja",
        "País Vasco",
        "Comunidad Foral de Navarra",
        "Principado de Asturias",
        "Illes Balears",
    }


def test_scrape_mobile_points_la_rioja_geocodes_only_stops_without_map(mocker):
    scraped = pd.DataFrame(
        {
            "lugar": ["Logroño - Cosme García", "LARDERO"],
            "localidad": ["Logroño", "LARDERO"],
            "direccion": ["Ies Cosme García", "C/ Los Cedros, 2"],
            "fecha": ["28/10/2026", "03/11/2026"],
            "horario": ["09:30-13:45", "17:30-21:00"],
            "url": [
                "https://www.bancosangrerioja.org/colecta?c=5013",
                "https://www.bancosangrerioja.org/colecta?c=5042",
            ],
            "latitude": [42.455, None],
            "longitude": [-2.451745, None],
        }
    )

    def fake_geocode_points(df, geocoding_cache, address_column):
        df["longitude"] = -2.5
        df["latitude"] = 42.5
        return df

    mocker.patch("main.la_rioja.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    geocode = mocker.patch("main.geocode_points", side_effect=fake_geocode_points)

    df = main.scrape_mobile_points_la_rioja()

    assert geocode.call_args.args[2] == "address_direccion"
    addresses = geocode.call_args.args[0]["address_direccion"]
    assert pd.isna(addresses.iloc[0])
    assert addresses.iloc[1] == "C/ Los Cedros, 2, LARDERO, La Rioja, Spain"
    # The page's own coordinates win; only the map-less stop takes the geocode
    assert df["latitude"].tolist() == [42.455, 42.5]
    assert df["longitude"].tolist() == [-2.451745, -2.5]
    assert df["name"].tolist() == [
        "Equipo móvil en Logroño - Cosme García",
        "Equipo móvil en LARDERO",
    ]
    assert df["opening_hours"].iloc[0] == "2026 Oct 28 09:30-13:45"
    assert df["region"].tolist() == ["La Rioja", "La Rioja"]


def test_scrape_fixed_points_la_rioja_uses_hand_built_hours(mocker):
    scraped = pd.DataFrame(
        {
            "name": ["Banco de Sangre del Hospital San Pedro"],
            "localidad": ["Logroño"],
            "direccion": ["Hospital San Pedro"],
            "latitude": [42.451333],
            "longitude": [-2.427574],
            "horario": ["De lunes a viernes de 8 a 20 horas Sábados de 9 a 14 horas"],
            "url": ["https://www.bancosangrerioja.org/donacion/donde-donar-sangre"],
        }
    )
    lookup = {"Banco de Sangre del Hospital San Pedro": "Mo-Fr 08:00-20:00; PH off"}
    mocker.patch("main.la_rioja.scrape_fixed_points", return_value=scraped)
    mocker.patch("main.load_opening_hours_fijos", return_value=lookup)

    df = main.scrape_fixed_points_la_rioja()

    assert df["opening_hours"].iloc[0] == "Mo-Fr 08:00-20:00; PH off"
    assert df["region"].iloc[0] == "La Rioja"
    assert (
        df["gmaps_url"].iloc[0] == "https://www.google.com/maps?q=42.451333+-2.427574"
    )


def test_scrape_mobile_points_aragon_builds_title_and_venue_candidates(mocker):
    scraped = pd.DataFrame(
        {
            "title": ["Sariñena, en el Centro de Salud", "Amazon Data Huesca"],
            "who": ["Sariñena", "Amazon Data Huesca"],
            "venue": ["Centro de Salud", None],
            "fecha": ["28/10/2026", "05/11/2026"],
            "horario": ["17:30 a 21:00", "09:30 a 13:00"],
            "url": ["https://bancosangrearagon.org/extraccion/a/"] * 2,
        }
    )

    captured = {}

    def fake_geocode_points(df, geocoding_cache, address_columns):
        captured["address_columns"] = address_columns
        captured["df"] = df.copy()
        df["longitude"] = -0.1
        df["latitude"] = 41.8
        return df

    mocker.patch("main.aragon.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.refresh_places_cache", return_value=pd.DataFrame())
    mocker.patch("main.pd.read_json", return_value=NO_LOCATION_OVERRIDES)
    mocker.patch(
        "main.place_candidate",
        side_effect=lambda query, expected, cache, bounds: (
            main.PLACE_CACHE_PREFIX + query if expected == "Sariñena" else None
        ),
    )
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)

    df = main.scrape_mobile_points_aragon()

    assert captured["address_columns"] == [
        "address_title",
        "address_venue",
        "place_title",
    ]
    seen = captured["df"]
    assert seen["address_title"].iloc[0] == (
        "Sariñena, en el Centro de Salud, Aragón, Spain"
    )
    assert seen["address_venue"].iloc[0] == "Centro de Salud Sariñena, Aragón, Spain"
    # No ", en <venue>" part -> no venue candidate
    assert pd.isna(seen["address_venue"].iloc[1])
    assert seen["place_title"].iloc[0] == "place: Sariñena, en el Centro de Salud"
    assert pd.isna(seen["place_title"].iloc[1])
    assert df["name"].iloc[0] == "Equipo móvil en Sariñena, en el Centro de Salud"
    assert df["opening_hours"].iloc[0] == "2026 Oct 28 17:30-21:00"


def test_apply_location_overrides_matches_title_or_who():
    df = pd.DataFrame(
        {
            "title": [
                "Delegación de Hacienda, en el Sótano -1",
                "Delegación de Hacienda, en la Planta 2",
                "Biota, en el Antiguo Matadero",
                "Biota, en el Centro de Salud",
                "Sariñena, en el Centro de Salud",
            ],
            "who": [
                "Delegación de Hacienda",
                "Delegación de Hacienda",
                "Biota",
                "Biota",
                "Sariñena",
            ],
            "longitude": [0.0] * 5,
            "latitude": [0.0] * 5,
        }
    )
    overrides = pd.DataFrame(
        {
            "match": ["Delegación de Hacienda", "Biota, en el Antiguo Matadero"],
            "lugar": ["Agencia Tributaria", "Ayuntamiento de Biota"],
            "latitude": [41.65, 42.26],
            "longitude": [-0.89, -1.19],
        }
    )

    df = main.apply_location_overrides(df, overrides, ["who", "title"])

    # Organization overrides cover any room; town overrides only that venue
    assert df["latitude"].tolist() == [41.65, 41.65, 42.26, 0.0, 0.0]
    assert df["longitude"].tolist() == [-0.89, -0.89, -1.19, 0.0, 0.0]


def test_scrape_mobile_points_valencia_flags_restriction_and_plasma(mocker):
    scraped = pd.DataFrame(
        {
            "fecha": ["28/10/2026", "28/10/2026"],
            "poblacion": ["CASTELLÓ DE LA PLANA", "ELCHE"],
            "ubicacion": ["CASTELLÓN-PROP ...", "ELCHE-SOLO DONACIÓN DE PLASMA ..."],
            "horario": ["09:30-13:30, 16:30-20:30", "16:30-21:00"],
            "province": ["castellon", "alicante"],
            "venue": ["PROP", "ELCHE HOSPITAL GENERAL"],
            # NaN, not None: what a missing street address is after the
            # crawler's DataFrame join — must fall back to the venue
            "direccion": ["AVDA. HERMANOS BOU, S/N", float("nan")],
            "restriction": ["(SOLO EMPLEADOS)", None],
            "plasma_only": [False, True],
        }
    )

    captured = {}

    def fake_geocode_points(df, geocoding_cache, address_columns):
        captured["df"] = df.copy()
        df["longitude"] = -0.04
        df["latitude"] = 39.98
        return df

    mocker.patch("main.comunidad_valenciana.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.refresh_places_cache", return_value=pd.DataFrame())
    mocker.patch("main.place_candidate", return_value=None)
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)

    df = main.scrape_mobile_points_valencia()

    assert df["name"].tolist() == [
        "Equipo móvil en PROP (SOLO EMPLEADOS)",
        "Equipo móvil en ELCHE HOSPITAL GENERAL",
    ]
    assert df["localidad"].tolist() == ["Castelló De La Plana", "Elche"]
    assert df["sangre"].tolist() == [True, False]
    assert df["plasma"].tolist() == [False, True]
    assert df["opening_hours"].iloc[0] == "2026 Oct 28 09:30-13:30,16:30-20:30"
    assert captured["df"]["address_direccion"].iloc[1] == (
        "ELCHE HOSPITAL GENERAL, Elche, Comunidad Valenciana, Spain"
    )


def test_scrape_mobile_points_cataluna_skips_places_for_mobile_units(mocker):
    scraped = pd.DataFrame(
        {
            "localidad": ["Gavà", "Vielha e Mijaran"],
            "venue": ["Unidad móvil", "Palau d'Esports"],
            "direccion": ["Pl. Jaume Balmes", "Av. Garona, 35"],
            "fecha": ["28/10/2026", "27/10/2026"],
            "sangre": [True, False],
            "plasma": [False, True],
            "url": ["https://www.bancsang.net/x/", "https://www.bancsang.net/y/"],
            "horario": ["De 17:00 a 21:00", None],
        }
    )
    captured = {}

    def fake_refresh(queries, cache, bounds):
        captured["queries"] = queries
        return cache

    def fake_geocode_points(df, geocoding_cache, address_columns):
        df["longitude"] = 2.0
        df["latitude"] = 41.3
        return df

    mocker.patch("main.cataluna.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.refresh_places_cache", side_effect=fake_refresh)
    mocker.patch("main.place_candidate", return_value=None)
    mocker.patch("main.pd.read_json", return_value=NO_LOCATION_OVERRIDES)
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)

    df = main.scrape_mobile_points_cataluna()

    # The bus stop's venue text isn't searched; its street address is the spot
    assert captured["queries"] == {"Palau d'Esports, Vielha e Mijaran"}
    assert df["sangre"].tolist() == [True, False]
    assert df["opening_hours"].iloc[0] == "2026 Oct 28 17:00-21:00"
    # Plasma-only stops have no published hours
    assert pd.isna(df["opening_hours"].iloc[1])


def test_scrape_mobile_points_cataluna_pins_by_venue_or_street(mocker):
    scraped = pd.DataFrame(
        {
            "localidad": ["Subirats", "Badalona", "Badalona"],
            "venue": ["Ateneu (Ordal)", "Unidad móvil", "Unidad móvil"],
            "direccion": ["Pl. del Ateneu, s/n", "Pl. de la Plana", "Pl. Pep Ventura"],
            "fecha": ["31/10/2026"] * 3,
            "sangre": [True] * 3,
            "plasma": [False] * 3,
            "url": ["https://www.bancsang.net/x/"] * 3,
            "horario": ["De 17:00 a 21:00"] * 3,
        }
    )
    overrides = pd.DataFrame(
        {
            "match": ["Ateneu (Ordal), Subirats", "Pl. de la Plana, Badalona"],
            "lugar": ["Ateneu Ordalenc", "Plaça de la Plana"],
            "latitude": [41.3955, 41.4469],
            "longitude": [1.8496, 2.2451],
        }
    )

    def fake_geocode_points(df, geocoding_cache, address_columns):
        df["longitude"] = 0.0
        df["latitude"] = 0.0
        return df

    mocker.patch("main.cataluna.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.refresh_places_cache", side_effect=lambda q, c, b: c)
    mocker.patch("main.place_candidate", return_value=None)
    mocker.patch("main.pd.read_json", return_value=overrides)
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)

    df = main.scrape_mobile_points_cataluna()

    # Venue-keyed pin, street-keyed pin, and a different bus stop in the
    # same town left alone
    assert df["latitude"].tolist() == [41.3955, 41.4469, 0.0]


def test_scrape_mobile_points_galicia_builds_queries_and_marks_provisional(mocker):
    scraped = pd.DataFrame(
        {
            "area": ["ÁREA SANITARIA A CORUÑA E CEE"] * 2,
            "fecha": ["23/10/2026", "11/11/2026"],
            "concello": ["Sada", "A Coruña"],
            "lugar": ["SADA", "Bº NOVO MESOIRO (A CORUÑA)"],
            "direccion": [
                "UNIDADE MÓBIL DIANTE DA CASA DA XUVENTUDE",
                "UNIDADE MÓBIL NA ROTONDA",
            ],
            "place_text": ["CASA DA XUVENTUDE", "ROTONDA"],
            "horario": ["09:45 a 14:30 e 15:45 a 21:00", "15:30 a 21:00"],
            "provisional": [False, True],
            "url": ["https://ados.sergas.gal/cartafol/proximos-desprazamentos"] * 2,
        }
    )
    overrides = pd.DataFrame(
        {
            "match": ["ROTONDA, A Coruña"],
            "lugar": ["Rotonda de Mesoiro"],
            "latitude": [43.33],
            "longitude": [-8.43],
        }
    )
    captured = {}

    def fake_refresh(queries, cache, bounds):
        captured["queries"] = queries
        return cache

    def fake_place_candidate(query, expected, cache, bounds):
        captured.setdefault("expected", []).append(expected)
        return "place: " + query if query.startswith("CASA") else None

    def fake_geocode_points(df, geocoding_cache, address_columns):
        captured["best_query"] = df[address_columns].tolist()
        df["longitude"] = -8.3
        df["latitude"] = 43.3
        return df

    mocker.patch("main.galicia.scrape_mobile_points", return_value=scraped)
    mocker.patch("main.load_geocoding_cache", return_value=pd.DataFrame())
    mocker.patch("main.refresh_places_cache", side_effect=fake_refresh)
    mocker.patch("main.place_candidate", side_effect=fake_place_candidate)
    mocker.patch("main.pd.read_json", return_value=overrides)
    mocker.patch("main.geocode_points", side_effect=fake_geocode_points)

    df = main.scrape_mobile_points_galicia()

    # A place that's just the concello isn't repeated; a neighbourhood loses
    # its "Bº" marker and parenthesized town
    assert captured["queries"] == {
        "CASA DA XUVENTUDE, Sada",
        "ROTONDA, Novo Mesoiro, A Coruña",
    }
    assert captured["expected"] == ["SADA/Sada", "NOVO MESOIRO/A Coruña"]
    # An accepted Places result wins outright; otherwise the geocode is used
    assert captured["best_query"] == [
        "place: CASA DA XUVENTUDE, Sada",
        "ROTONDA, Novo Mesoiro, A Coruña, Galicia, Spain",
    ]
    assert df["name"].tolist() == [
        "Equipo móvil en Sada",
        "Equipo móvil en Bº Novo Mesoiro (A Coruña) (provisional)",
    ]
    assert df["latitude"].tolist() == [43.3, 43.33]
    assert df["opening_hours"].iloc[0] == "2026 Oct 23 09:45-14:30,15:45-21:00"


def test_title_galicia_name_keeps_particles_lowercase():
    assert main.title_galicia_name("O BARCO DE VALDEORRAS") == "O Barco de Valdeorras"
    assert main.title_galicia_name("ZONA DA FERRARÍA") == "Zona da Ferraría"
    assert main.title_galicia_name("DE PONTEVEDRA") == "De Pontevedra"


def test_scrape_mobile_points_pais_vasco_uses_listing_coords(mocker):
    scraped = pd.DataFrame(
        {
            "province": ["Bizkaia", "Bizkaia"],
            "localidad": ["Bilbao", "Bilbao"],
            "lugar": ["Bilbao Bombero Etxaniz - Solo Plasma/Cita", "Plaza Circular"],
            "direccion": ["Plaza Bombero Etxaniz 1", "Plaza Circular"],
            "latitude": [43.2584, 43.2613],
            "longitude": [-2.9398, -2.9275],
            "fecha": ["27/10/2026", "27/10/2026"],
            "horario": ["08:30-13:00, 14:00-18:30", "09:15-14:00"],
            "plasma_only": [True, False],
            "url": ["https://donantesdesangre.eus/donde-donar/"] * 2,
        }
    )
    mocker.patch("main.pais_vasco.scrape_mobile_points", return_value=scraped)
    geocode = mocker.patch("main.geocode_points")

    df = main.scrape_mobile_points_pais_vasco()

    geocode.assert_not_called()
    assert df["latitude"].tolist() == [43.2584, 43.2613]
    assert df["sangre"].tolist() == [False, True]
    assert df["plasma"].tolist() == [True, False]
    assert df["opening_hours"].iloc[0] == "2026 Oct 27 08:30-13:00,14:00-18:30"


def test_scrape_fixed_points_baleares_uses_hand_built_hours(mocker):
    scraped = pd.DataFrame(
        {
            "name": ["Palma (Mallorca). Banco de sangre", "Eivissa"],
            "localidad": ["Palma", "Eivissa"],
            "direccion": ["Rosselló i Cazador, 20", "Hospital Can Misses"],
            "horario": ["De lunes a viernes, de 8:00 a 20:30 h", None],
            "latitude": [39.581953, 38.916526],
            "longitude": [2.653389, 1.418271],
            "url": ["https://www.donasang.org/a", "https://www.donasang.org/b"],
        }
    )
    lookup = {
        "Palma (Mallorca). Banco de sangre": "Mo-Fr 08:00-20:30; Sa 09:00-13:30; PH off"
    }
    mocker.patch("main.balears.scrape_fixed_points", return_value=scraped)
    mocker.patch("main.load_opening_hours_fijos", return_value=lookup)

    df = main.scrape_fixed_points_baleares()

    assert df["opening_hours"].iloc[0] == "Mo-Fr 08:00-20:30; Sa 09:00-13:30; PH off"
    # Eivissa publishes no fixed hours, so it has no lookup entry.
    assert pd.isna(df["opening_hours"].iloc[1])
    assert df["region"].tolist() == ["Illes Balears", "Illes Balears"]
    assert df["gmaps_url"].iloc[0] == "https://www.google.com/maps?q=39.581953+2.653389"


def test_scrape_mobile_points_baleares_flags_aferesis_as_plasma(mocker):
    scraped = pd.DataFrame(
        {
            "lugar": ["Banc de Sang i Teixits", "AFERESI / AFERESIS MANACOR"],
            "localidad": ["Palma", "Manacor"],
            "direccion": ["Rosselló i Caçador, 20", "CENTRE SANITARI C/ SIMO TORT, 19"],
            "fecha": ["28/10/2026", "29/10/2026"],
            "horario": ["08:00-20:30", "16:30-20:30"],
            "url": [
                "https://www.donasang.org/on-puc-donar/es_calendari/46968/palma",
                "https://www.donasang.org/on-puc-donar/es_calendari/46978/manacor",
            ],
            "aferesis": [False, True],
            "latitude": [39.582059, 39.567614],
            "longitude": [2.653558, 3.202958],
        }
    )
    mocker.patch("main.balears.scrape_mobile_points", return_value=scraped)

    df = main.scrape_mobile_points_baleares()

    assert df["name"].tolist() == [
        "Equipo móvil en Banc de Sang i Teixits",
        "Equipo móvil en AFERESI / AFERESIS MANACOR",
    ]
    # Only aféresis sessions are flagged (plasma, not sangre); others stay unset.
    assert pd.isna(df["plasma"].iloc[0])
    assert pd.isna(df["sangre"].iloc[0])
    assert df["plasma"].iloc[1] == True
    assert df["sangre"].iloc[1] == False
    assert df["opening_hours"].notna().all()
    assert df["region"].tolist() == ["Illes Balears", "Illes Balears"]
