import os
import tempfile
from unittest import TestCase

import boto3
import numpy as np
import pandas as pd
import pytest
from moto import mock_s3

from datasets import Features, Sequence, Value, load_from_disk
from datasets.arrow_dataset import Dataset
from datasets.dataset_dict import DatasetDict
from datasets.filesystems import S3FileSystem

from .utils import require_tf, require_torch


class DatasetDictTest(TestCase):
    def _create_dummy_dataset(self, multiple_columns=False):
        if multiple_columns:
            data = {"col_1": [3, 2, 1, 0], "col_2": ["a", "b", "c", "d"]}
            dset = Dataset.from_dict(data)
        else:
            dset = Dataset.from_dict(
                {"filename": ["my_name-train" + "_" + "{:03d}".format(x) for x in np.arange(30).tolist()]}
            )
        return dset

    def _create_dummy_dataset_dict(self, multiple_columns=False) -> DatasetDict:
        return DatasetDict(
            {
                "train": self._create_dummy_dataset(multiple_columns=multiple_columns),
                "test": self._create_dummy_dataset(multiple_columns=multiple_columns),
            }
        )

    def test_flatten(self):
        dset_split = Dataset.from_dict(
            {"a": [{"b": {"c": ["text"]}}] * 10, "foo": [1] * 10},
            features=Features({"a": {"b": Sequence({"c": Value("string")})}, "foo": Value("int64")}),
        )
        dset = DatasetDict({"train": dset_split, "test": dset_split})
        dset.flatten_()
        self.assertDictEqual(dset.column_names, {"train": ["a.b.c", "foo"], "test": ["a.b.c", "foo"]})
        self.assertListEqual(list(dset["train"].features.keys()), ["a.b.c", "foo"])
        self.assertDictEqual(
            dset["train"].features, Features({"a.b.c": Sequence(Value("string")), "foo": Value("int64")})
        )
        del dset

    def test_set_format_numpy(self):
        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        dset.set_format(type="numpy", columns=["col_1"])
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0]), 1)
            self.assertIsInstance(dset_split[0]["col_1"], np.int64)
            self.assertEqual(dset_split[0]["col_1"].item(), 3)

        dset.reset_format()
        with dset.formatted_as(type="numpy", columns=["col_1"]):
            for dset_split in dset.values():
                self.assertEqual(len(dset_split[0]), 1)
                self.assertIsInstance(dset_split[0]["col_1"], np.int64)
                self.assertEqual(dset_split[0]["col_1"].item(), 3)

        for dset_split in dset.values():
            self.assertEqual(dset_split.format["type"], None)
            self.assertEqual(dset_split.format["format_kwargs"], {})
            self.assertEqual(dset_split.format["columns"], dset_split.column_names)
            self.assertEqual(dset_split.format["output_all_columns"], False)

        dset.set_format(type="numpy", columns=["col_1"], output_all_columns=True)
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0]), 2)
            self.assertIsInstance(dset_split[0]["col_2"], str)
            self.assertEqual(dset_split[0]["col_2"], "a")

        dset.set_format(type="numpy", columns=["col_1", "col_2"])
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0]), 2)
            self.assertIsInstance(dset_split[0]["col_2"], np.str_)
            self.assertEqual(dset_split[0]["col_2"].item(), "a")
        del dset

    @require_torch
    def test_set_format_torch(self):
        import torch

        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        dset.set_format(type="torch", columns=["col_1"])
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0]), 1)
            self.assertIsInstance(dset_split[0]["col_1"], torch.Tensor)
            self.assertListEqual(list(dset_split[0]["col_1"].shape), [])
            self.assertEqual(dset_split[0]["col_1"].item(), 3)

        dset.set_format(type="torch", columns=["col_1"], output_all_columns=True)
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0]), 2)
            self.assertIsInstance(dset_split[0]["col_2"], str)
            self.assertEqual(dset_split[0]["col_2"], "a")

        dset.set_format(type="torch", columns=["col_1", "col_2"])
        for dset_split in dset.values():
            with self.assertRaises(TypeError):
                dset_split[0]
        del dset

    @require_tf
    def test_set_format_tf(self):
        import tensorflow as tf

        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        dset.set_format(type="tensorflow", columns=["col_1"])
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0]), 1)
            self.assertIsInstance(dset_split[0]["col_1"], tf.Tensor)
            self.assertListEqual(list(dset_split[0]["col_1"].shape), [])
            self.assertEqual(dset_split[0]["col_1"].numpy().item(), 3)

        dset.set_format(type="tensorflow", columns=["col_1"], output_all_columns=True)
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0]), 2)
            self.assertIsInstance(dset_split[0]["col_2"], str)
            self.assertEqual(dset_split[0]["col_2"], "a")

        dset.set_format(type="tensorflow", columns=["col_1", "col_2"])
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0]), 2)
            self.assertEqual(dset_split[0]["col_2"].numpy().decode("utf-8"), "a")
        del dset

    def test_set_format_pandas(self):
        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        dset.set_format(type="pandas", columns=["col_1"])
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0].columns), 1)
            self.assertIsInstance(dset_split[0], pd.DataFrame)
            self.assertListEqual(list(dset_split[0].shape), [1, 1])
            self.assertEqual(dset_split[0]["col_1"].item(), 3)

        dset.set_format(type="pandas", columns=["col_1", "col_2"])
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0].columns), 2)
            self.assertEqual(dset_split[0]["col_2"].item(), "a")
        del dset

    def test_set_transform(self):
        def transform(batch):
            return {k: [str(i).upper() for i in v] for k, v in batch.items()}

        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        dset.set_transform(transform=transform, columns=["col_1"])
        for dset_split in dset.values():
            self.assertEqual(dset_split.format["type"], "custom")
            self.assertEqual(len(dset_split[0].keys()), 1)
            self.assertEqual(dset_split[0]["col_1"], "3")
            self.assertEqual(dset_split[:2]["col_1"], ["3", "2"])
            self.assertEqual(dset_split["col_1"][:2], ["3", "2"])

        prev_format = dset[list(dset.keys())[0]].format
        for dset_split in dset.values():
            dset_split.set_format(**dset_split.format)
            self.assertEqual(prev_format, dset_split.format)

        dset.set_transform(transform=transform, columns=["col_1", "col_2"])
        for dset_split in dset.values():
            self.assertEqual(len(dset_split[0].keys()), 2)
            self.assertEqual(dset_split[0]["col_2"], "A")
        del dset

    def test_with_format(self):
        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        dset2 = dset.with_format("numpy", columns=["col_1"])
        dset.set_format("numpy", columns=["col_1"])
        for dset_split, dset_split2 in zip(dset.values(), dset2.values()):
            self.assertDictEqual(dset_split.format, dset_split2.format)
        del dset, dset2

    def test_with_transform(self):
        def transform(batch):
            return {k: [str(i).upper() for i in v] for k, v in batch.items()}

        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        dset2 = dset.with_transform(transform, columns=["col_1"])
        dset.set_transform(transform, columns=["col_1"])
        for dset_split, dset_split2 in zip(dset.values(), dset2.values()):
            self.assertDictEqual(dset_split.format, dset_split2.format)
        del dset, dset2

    def test_cast_(self):
        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        features = dset["train"].features
        features["col_1"] = Value("float64")
        dset.cast_(features)
        for dset_split in dset.values():
            self.assertEqual(dset_split.num_columns, 2)
            self.assertEqual(dset_split.features["col_1"], Value("float64"))
            self.assertIsInstance(dset_split[0]["col_1"], float)
        del dset

    def test_remove_columns_(self):
        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        dset.remove_columns_(column_names="col_1")
        for dset_split in dset.values():
            self.assertEqual(dset_split.num_columns, 1)
            self.assertListEqual(list(dset_split.column_names), ["col_2"])

        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        dset.remove_columns_(column_names=["col_1", "col_2"])
        for dset_split in dset.values():
            self.assertEqual(dset_split.num_columns, 0)
        del dset

    def test_rename_column_(self):
        dset = self._create_dummy_dataset_dict(multiple_columns=True)
        dset.rename_column_(original_column_name="col_1", new_column_name="new_name")
        for dset_split in dset.values():
            self.assertEqual(dset_split.num_columns, 2)
            self.assertListEqual(list(dset_split.column_names), ["new_name", "col_2"])
        del dset

    def test_map(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dsets = self._create_dummy_dataset_dict()

            mapped_dsets_1: DatasetDict = dsets.map(lambda ex: {"foo": ["bar"] * len(ex["filename"])}, batched=True)
            self.assertListEqual(list(dsets.keys()), list(mapped_dsets_1.keys()))
            self.assertListEqual(mapped_dsets_1["train"].column_names, ["filename", "foo"])

            cache_file_names = {
                "train": os.path.join(tmp_dir, "train.arrow"),
                "test": os.path.join(tmp_dir, "test.arrow"),
            }
            mapped_dsets_2: DatasetDict = mapped_dsets_1.map(
                lambda ex: {"bar": ["foo"] * len(ex["filename"])}, batched=True, cache_file_names=cache_file_names
            )
            self.assertListEqual(list(dsets.keys()), list(mapped_dsets_2.keys()))
            self.assertListEqual(sorted(mapped_dsets_2["train"].column_names), sorted(["filename", "foo", "bar"]))
            del dsets, mapped_dsets_1, mapped_dsets_2

    def test_filter(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dsets = self._create_dummy_dataset_dict()

            filtered_dsets_1: DatasetDict = dsets.filter(lambda ex: int(ex["filename"].split("_")[-1]) < 10)
            self.assertListEqual(list(dsets.keys()), list(filtered_dsets_1.keys()))
            self.assertEqual(len(filtered_dsets_1["train"]), 10)

            cache_file_names = {
                "train": os.path.join(tmp_dir, "train.arrow"),
                "test": os.path.join(tmp_dir, "test.arrow"),
            }
            filtered_dsets_2: DatasetDict = filtered_dsets_1.filter(
                lambda ex: int(ex["filename"].split("_")[-1]) < 5, cache_file_names=cache_file_names
            )
            self.assertListEqual(list(dsets.keys()), list(filtered_dsets_2.keys()))
            self.assertEqual(len(filtered_dsets_2["train"]), 5)
            del dsets, filtered_dsets_1, filtered_dsets_2

    def test_sort(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dsets = self._create_dummy_dataset_dict()

            sorted_dsets_1: DatasetDict = dsets.sort("filename")
            self.assertListEqual(list(dsets.keys()), list(sorted_dsets_1.keys()))
            self.assertListEqual(
                [f.split("_")[-1] for f in sorted_dsets_1["train"]["filename"]],
                sorted("{:03d}".format(x) for x in range(30)),
            )

            indices_cache_file_names = {
                "train": os.path.join(tmp_dir, "train.arrow"),
                "test": os.path.join(tmp_dir, "test.arrow"),
            }
            sorted_dsets_2: DatasetDict = sorted_dsets_1.sort(
                "filename", indices_cache_file_names=indices_cache_file_names, reverse=True
            )
            self.assertListEqual(list(dsets.keys()), list(sorted_dsets_2.keys()))
            self.assertListEqual(
                [f.split("_")[-1] for f in sorted_dsets_2["train"]["filename"]],
                sorted(("{:03d}".format(x) for x in range(30)), reverse=True),
            )
            del dsets, sorted_dsets_1, sorted_dsets_2

    def test_shuffle(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dsets = self._create_dummy_dataset_dict()

            indices_cache_file_names = {
                "train": os.path.join(tmp_dir, "train.arrow"),
                "test": os.path.join(tmp_dir, "test.arrow"),
            }
            seeds = {
                "train": 1234,
                "test": 1234,
            }
            dsets_shuffled = dsets.shuffle(
                seeds=seeds, indices_cache_file_names=indices_cache_file_names, load_from_cache_file=False
            )
            self.assertListEqual(dsets_shuffled["train"]["filename"], dsets_shuffled["test"]["filename"])

            self.assertEqual(len(dsets_shuffled["train"]), 30)
            self.assertEqual(dsets_shuffled["train"][0]["filename"], "my_name-train_028")
            self.assertEqual(dsets_shuffled["train"][2]["filename"], "my_name-train_010")
            self.assertDictEqual(dsets["train"].features, Features({"filename": Value("string")}))
            self.assertDictEqual(dsets_shuffled["train"].features, Features({"filename": Value("string")}))

            # Reproducibility
            indices_cache_file_names_2 = {
                "train": os.path.join(tmp_dir, "train_2.arrow"),
                "test": os.path.join(tmp_dir, "test_2.arrow"),
            }
            dsets_shuffled_2 = dsets.shuffle(
                seeds=seeds, indices_cache_file_names=indices_cache_file_names_2, load_from_cache_file=False
            )
            self.assertListEqual(dsets_shuffled["train"]["filename"], dsets_shuffled_2["train"]["filename"])

            seeds = {
                "train": 1234,
                "test": 1,
            }
            indices_cache_file_names_3 = {
                "train": os.path.join(tmp_dir, "train_3.arrow"),
                "test": os.path.join(tmp_dir, "test_3.arrow"),
            }
            dsets_shuffled_3 = dsets.shuffle(
                seeds=seeds, indices_cache_file_names=indices_cache_file_names_3, load_from_cache_file=False
            )
            self.assertNotEqual(dsets_shuffled_3["train"]["filename"], dsets_shuffled_3["test"]["filename"])

            # other input types
            dsets_shuffled_int = dsets.shuffle(42)
            dsets_shuffled_alias = dsets.shuffle(seed=42)
            dsets_shuffled_none = dsets.shuffle()
            self.assertEqual(len(dsets_shuffled_int["train"]), 30)
            self.assertEqual(len(dsets_shuffled_alias["train"]), 30)
            self.assertEqual(len(dsets_shuffled_none["train"]), 30)

            del dsets, dsets_shuffled, dsets_shuffled_2, dsets_shuffled_3
            del dsets_shuffled_int, dsets_shuffled_alias, dsets_shuffled_none

    def test_check_values_type(self):
        dsets = self._create_dummy_dataset_dict()
        dsets["bad_split"] = None
        self.assertRaises(TypeError, dsets.map, lambda x: x)
        self.assertRaises(TypeError, dsets.filter, lambda x: True)
        self.assertRaises(TypeError, dsets.shuffle)
        self.assertRaises(TypeError, dsets.sort, "filename")
        del dsets

    def test_serialization(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dsets = self._create_dummy_dataset_dict()
            dsets.save_to_disk(tmp_dir)
            del dsets
            dsets = DatasetDict.load_from_disk(tmp_dir)
            self.assertListEqual(sorted(dsets), ["test", "train"])
            self.assertEqual(len(dsets["train"]), 30)
            self.assertListEqual(dsets["train"].column_names, ["filename"])
            self.assertEqual(len(dsets["test"]), 30)
            self.assertListEqual(dsets["test"].column_names, ["filename"])

            del dsets["test"]
            dsets.save_to_disk(tmp_dir)
            del dsets
            dsets = DatasetDict.load_from_disk(tmp_dir)
            self.assertListEqual(sorted(dsets), ["train"])
            self.assertEqual(len(dsets["train"]), 30)
            self.assertListEqual(dsets["train"].column_names, ["filename"])
            del dsets

    def test_load_from_disk(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            dsets = self._create_dummy_dataset_dict()
            dsets.save_to_disk(tmp_dir)
            del dsets
            dsets = load_from_disk(tmp_dir)
            self.assertListEqual(sorted(dsets), ["test", "train"])
            self.assertEqual(len(dsets["train"]), 30)
            self.assertListEqual(dsets["train"].column_names, ["filename"])
            self.assertEqual(len(dsets["test"]), 30)
            self.assertListEqual(dsets["test"].column_names, ["filename"])
            del dsets

    @mock_s3
    def test_save_and_load_to_s3(self):
        # Mocked AWS Credentials for moto.
        os.environ["AWS_ACCESS_KEY_ID"] = "fake_access_key"
        os.environ["AWS_SECRET_ACCESS_KEY"] = "fake_secret_key"
        os.environ["AWS_SECURITY_TOKEN"] = "fake_secrurity_token"
        os.environ["AWS_SESSION_TOKEN"] = "fake_session_token"

        s3 = boto3.client("s3", region_name="us-east-1")
        mock_bucket = "moto-mock-s3-bucket"
        # We need to create the bucket since this is all in Moto's 'virtual' AWS account
        s3.create_bucket(Bucket=mock_bucket)
        dataset_path = f"s3://{mock_bucket}/datasets/dict"

        fs = S3FileSystem(key="fake_access_key", secret="fake_secret")

        dsets = self._create_dummy_dataset_dict()
        dsets.save_to_disk(dataset_path, fs)

        del dsets

        dsets = load_from_disk(dataset_path, fs)

        self.assertListEqual(sorted(dsets), ["test", "train"])
        self.assertEqual(len(dsets["train"]), 30)
        self.assertListEqual(dsets["train"].column_names, ["filename"])
        self.assertEqual(len(dsets["test"]), 30)
        self.assertListEqual(dsets["test"].column_names, ["filename"])
        del dsets


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
@pytest.mark.parametrize("split", [None, "train", "test"])
def test_datasetdict_from_csv(split, features, csv_path, tmp_path):
    if split:
        path = {split: csv_path}
    else:
        split = "train"
        path = {"train": csv_path, "test": csv_path}
    cache_dir = tmp_path / "cache"
    # CSV file loses col_1 string dtype information: default now is "int64" instead of "string"
    default_expected_features = {"col_1": "int64", "col_2": "int64", "col_3": "float64"}
    expected_features = features.copy() if features else default_expected_features
    features = Features({feature: Value(dtype) for feature, dtype in features.items()}) if features else None

    dataset = DatasetDict.from_csv(path, features=features, cache_dir=cache_dir)
    assert isinstance(dataset, DatasetDict)
    dataset = dataset[split]
    assert dataset.num_rows == 4
    assert dataset.num_columns == 3
    assert dataset.column_names == ["col_1", "col_2", "col_3"]
    assert dataset.split == split
    for feature, expected_dtype in expected_features.items():
        assert dataset.features[feature].dtype == expected_dtype
