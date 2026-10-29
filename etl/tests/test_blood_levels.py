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
    mocker.patch(
        "utils.crawl.madrid.scrape_blood_levels", return_value=_scraped_levels()
    )
    mocker.patch(
        "utils.crawl.castilla_y_leon.scrape_blood_levels",
        return_value=_scraped_levels(),
    )
    mocker.patch(
        "utils.crawl.galicia.scrape_blood_levels", return_value=_scraped_levels()
    )
    mocker.patch(
        "utils.crawl.la_rioja.scrape_blood_levels", return_value=_scraped_levels()
    )
    mocker.patch(
        "utils.crawl.pais_vasco.scrape_blood_levels", return_value=_scraped_levels()
    )
    mocker.patch(
        "utils.crawl.asturias.scrape_blood_levels", return_value=_scraped_levels()
    )
    mocker.patch(
        "utils.crawl.balears.scrape_blood_levels", return_value=_scraped_levels()
    )
    mocker.patch(
        "utils.crawl.murcia.scrape_blood_levels", return_value=_scraped_levels()
    )


def test_process_blood_levels_appends_to_blood_levels_table(mocker):
    _patch_all_blood_level_sources(mocker)
    mock_to_db = mocker.patch("utils.db.to_db")

    main.process_blood_levels()

    mock_to_db.assert_called_once()
    table_name = mock_to_db.call_args.args[1]
    assert table_name == "blood_levels"
    assert mock_to_db.call_args.kwargs["if_exists"] == "append"


def test_process_blood_levels_adds_source_and_single_timestamp(mocker):
    _patch_all_blood_level_sources(mocker)
    mock_to_db = mocker.patch("utils.db.to_db")

    main.process_blood_levels()

    uploaded = mock_to_db.call_args.args[0]
    assert set(uploaded["source"]) == {
        "donarsangre.org",
        "centrodehemoterapiacyl.es",
        "ados.sergas.gal",
        "bancosangrerioja.org",
        "donantesdesangre.eus",
        "donasturias.org",
        "donasang.org",
        "murciasalud.es",
    }
    assert set(uploaded["region"]) == {
        "Comunidad de Madrid",
        "Castilla y León",
        "Galicia",
        "La Rioja",
        "País Vasco",
        "Principado de Asturias",
        "Illes Balears",
        "Región de Murcia",
    }
    # One snapshot per run: every row shares the same timestamp
    assert uploaded["updated_at"].nunique() == 1
