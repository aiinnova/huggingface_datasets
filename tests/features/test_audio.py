import sys

import pytest

from datasets import Dataset
from datasets.features import Audio, Features


def test_audio_instantiation():
    audio = Audio()
    assert audio.id is None
    assert audio.dtype == "dict"
    assert audio.pa_type is None
    assert audio._type == "Audio"


@pytest.mark.skipif(
    sys.platform == "linux", reason="linux requires libsndfile installed using distribution package manager"
)
def test_audio_decode_example(shared_datadir):
    audio_path = str(shared_datadir / "test_audio_44100.wav")
    audio = Audio()
    decoded_example = audio.decode_example(audio_path)
    assert decoded_example.keys() == {"array", "sampling_rate"}
    assert decoded_example["array"].shape == (202311,)
    assert decoded_example["sampling_rate"] == 44100


@pytest.mark.skipif(
    sys.platform == "linux", reason="linux requires libsndfile installed using distribution package manager"
)
def test_dataset_with_audio_feature(shared_datadir):
    audio_path = str(shared_datadir / "test_audio_44100.wav")
    data = {"file": [audio_path]}
    features = Features({"file": Audio()})
    dset = Dataset.from_dict(data, features=features).map(features.decode_example)
    assert dset.shape == (1, 1)
    assert dset.column_names == ["file"]
    assert isinstance(dset[0]["file"], dict)
    assert dset[0]["file"].keys() == {"array", "sampling_rate"}
    assert len(dset[0]["file"]["array"]) == 202311  # TODO: to numpy?
    assert dset[0]["file"]["sampling_rate"] == 44100
