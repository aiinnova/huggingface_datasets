import csv

import pytest

from datasets import Features, NamedSplit, Value
from datasets.io.csv import CsvDatasetReader


DATA = [
    {"col_1": "0", "col_2": 0, "col_3": 0.0},
    {"col_1": "1", "col_2": 1, "col_3": 1.0},
    {"col_1": "2", "col_2": 2, "col_3": 2.0},
    {"col_1": "3", "col_2": 3, "col_3": 3.0},
]


@pytest.fixture(scope="session")
def csv_path(tmp_path_factory):
    path = str(tmp_path_factory.mktemp("data") / "dataset.csv")
    with open(path, "w") as f:
        writer = csv.DictWriter(f, fieldnames=["col_1", "col_2", "col_3"])
        writer.writeheader()
        for item in DATA:
            writer.writerow(item)
    return path


@pytest.mark.parametrize(
    "features",
    [
        None,
        {"col_1": "string", "col_2": "int64", "col_3": "float64"},
        {"col_1": "string", "col_2": "string", "col_3": "string"},
        {"col_1": "int32", "col_2": "int32", "col_3": "int32"},
        {"col_1": "float32", "col_2": "float32", "col_3": "float32"},
    ],
)
@pytest.mark.parametrize("split", [None, NamedSplit("train")])
@pytest.mark.parametrize("path_type", [str, list, dict])
def test_dataset_csv_builder(path_type, split, csv_path, features, tmp_path):
    if issubclass(path_type, str):
        path = csv_path
    elif issubclass(path_type, list):
        path = [csv_path]
    elif issubclass(path_type, dict):
        path = {"train": csv_path}
    cache_dir = tmp_path / "cache"

    # CSV file loses col_1 string dtype information: default now is "int64" instead of "string"
    default_expected_features = {"col_1": "int64", "col_2": "int64", "col_3": "float64"}
    expected_features = features.copy() if features else default_expected_features
    features = Features({feature: Value(dtype) for feature, dtype in features.items()}) if features else None

    ds = CsvDatasetReader(path, split=split, features=features, cache_dir=cache_dir).read()
    ds = ds if split else ds["train"]  # # if split is None: ds.num_rows = {'train': 4} instead of 4
    assert ds.num_rows == 4
    assert ds.num_columns == 3
    assert ds.column_names == ["col_1", "col_2", "col_3"]
    assert ds.split == "train"
    for feature, expected_dtype in expected_features.items():
        assert ds.features[feature].dtype == expected_dtype