"""Tests for process_blood_levels — append-mode upload with run metadata."""

import pandas as pd

import main


def _scraped_levels():
    return pd.DataFrame(
        {
            "blood_type": ["0-", "A+", "AB+"],
            "status": ["urgent", "soon", "stable"],
            "level": [1, 2, 3],
            "label": [
                "Dona hoy",
                "Dona en los próximos días",
                "Dona dentro de unas semanas",
            ],
        }
    )


def test_process_blood_levels_appends_to_blood_levels_table(mocker):
    mocker.patch("main.scrape_blood_levels", return_value=_scraped_levels())
    mock_to_db = mocker.patch("main.to_db")

    main.process_blood_levels()

    mock_to_db.assert_called_once()
    table_name = mock_to_db.call_args.args[1]
    assert table_name == "blood_levels"
    assert mock_to_db.call_args.kwargs["if_exists"] == "append"


def test_process_blood_levels_adds_source_and_single_timestamp(mocker):
    mocker.patch("main.scrape_blood_levels", return_value=_scraped_levels())
    mock_to_db = mocker.patch("main.to_db")

    main.process_blood_levels()

    uploaded = mock_to_db.call_args.args[0]
    assert set(uploaded["source"]) == {"donarsangre.org"}
    assert set(uploaded["region"]) == {"Comunidad de Madrid"}
    # One snapshot per run: every row shares the same timestamp
    assert uploaded["updated_at"].nunique() == 1
