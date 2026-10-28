"""Tests for process_blood_levels — append-mode upload with run metadata."""

import pandas as pd

import main


def _scraped_levels():
    return pd.DataFrame(
        {
            "blood_type": ["0-", "A+", "AB+"],
            "status": ["red", "orange", "green"],
            "level": [1, 2, 3],
            "label": [
                "Dona hoy",
                "Dona en los próximos días",
                "Dona dentro de unas semanas",
            ],
        }
    )


def _patch_all_blood_level_sources(mocker):
    mocker.patch("main.madrid.scrape_blood_levels", return_value=_scraped_levels())
    mocker.patch(
        "main.castilla_y_leon.scrape_blood_levels", return_value=_scraped_levels()
    )
    mocker.patch("main.galicia.scrape_blood_levels", return_value=_scraped_levels())
    mocker.patch("main.pais_vasco.scrape_blood_levels", return_value=_scraped_levels())
    mocker.patch("main.asturias.scrape_blood_levels", return_value=_scraped_levels())


def test_process_blood_levels_appends_to_blood_levels_table(mocker):
    _patch_all_blood_level_sources(mocker)
    mock_to_db = mocker.patch("main.to_db")

    main.process_blood_levels()

    mock_to_db.assert_called_once()
    table_name = mock_to_db.call_args.args[1]
    assert table_name == "blood_levels"
    assert mock_to_db.call_args.kwargs["if_exists"] == "append"


def test_process_blood_levels_adds_source_and_single_timestamp(mocker):
    _patch_all_blood_level_sources(mocker)
    mock_to_db = mocker.patch("main.to_db")

    main.process_blood_levels()

    uploaded = mock_to_db.call_args.args[0]
    assert set(uploaded["source"]) == {
        "donarsangre.org",
        "centrodehemoterapiacyl.es",
        "ados.sergas.gal",
        "donantesdesangre.eus",
        "donasturias.org",
    }
    assert set(uploaded["region"]) == {
        "Comunidad de Madrid",
        "Castilla y León",
        "Galicia",
        "País Vasco",
        "Principado de Asturias",
    }
    # One snapshot per run: every row shares the same timestamp
    assert uploaded["updated_at"].nunique() == 1
