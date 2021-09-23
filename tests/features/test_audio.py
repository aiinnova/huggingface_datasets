import importlib

import pytest

from datasets import Dataset
from datasets.features import Audio, Features


pytestmark = pytest.mark.audio

require_soundfile = pytest.mark.skipif(
    importlib.util.find_spec("soundfile") is None,
    reason="Test requires 'soundfile'; Linux requires libsndfile installed using distribution package manager",
)
require_sox = pytest.mark.skipif(importlib.util.find_spec("sox") is None, reason="Test requires 'sox'")
require_torchaudio = pytest.mark.skipif(
    importlib.util.find_spec("torchaudio") is None, reason="Test requires 'torchaudio'"
)


def test_audio_instantiation():
    audio = Audio()
    assert audio.id is None
    assert audio.dtype == "dict"
    assert audio.pa_type is None
    assert audio._type == "Audio"


@require_soundfile
def test_audio_decode_example(shared_datadir):
    audio_path = str(shared_datadir / "test_audio_44100.wav")
    audio = Audio()
    decoded_example = audio.decode_example(audio_path)
    assert decoded_example.keys() == {"path", "array", "sampling_rate"}
    assert decoded_example["path"] == audio_path
    assert decoded_example["array"].shape == (202311,)
    assert decoded_example["sampling_rate"] == 44100


@require_soundfile
def test_audio_resampling(shared_datadir):
    audio_path = str(shared_datadir / "test_audio_44100.wav")
    audio = Audio(sampling_rate=16000)
    decoded_example = audio.decode_example(audio_path)
    assert decoded_example.keys() == {"path", "array", "sampling_rate"}
    assert decoded_example["path"] == audio_path
    assert decoded_example["array"].shape == (73401,)
    assert decoded_example["sampling_rate"] == 16000


@require_sox
@require_torchaudio
def test_audio_decode_example_mp3(shared_datadir):
    audio_path = str(shared_datadir / "test_audio_44100.mp3")
    audio = Audio()
    decoded_example = audio.decode_example(audio_path)
    assert decoded_example.keys() == {"path", "array", "sampling_rate"}
    assert decoded_example["path"] == audio_path
    assert decoded_example["array"].shape == (73401,)
    assert decoded_example["sampling_rate"] == 44100


@require_soundfile
def test_dataset_with_audio_feature(shared_datadir):
    audio_path = str(shared_datadir / "test_audio_44100.wav")
    data = {"audio": [audio_path]}
    features = Features({"audio": Audio()})
    dset = Dataset.from_dict(data, features=features)
    item = dset[0]
    assert item.keys() == {"audio"}
    assert item["audio"].keys() == {"path", "array", "sampling_rate"}
    assert item["audio"]["path"] == audio_path
    assert item["audio"]["array"].shape == (202311,)
    assert item["audio"]["sampling_rate"] == 44100
    batch = dset[:1]
    assert batch.keys() == {"audio"}
    assert len(batch["audio"]) == 1
    assert batch["audio"][0].keys() == {"path", "array", "sampling_rate"}
    assert batch["audio"][0]["path"] == audio_path
    assert batch["audio"][0]["array"].shape == (202311,)
    assert batch["audio"][0]["sampling_rate"] == 44100


@require_soundfile
def test_formatted_dataset_with_audio_feature(shared_datadir):
    audio_path = str(shared_datadir / "test_audio_44100.wav")
    data = {"audio": [audio_path, audio_path]}
    features = Features({"audio": Audio()})
    dset = Dataset.from_dict(data, features=features)
    with dset.formatted_as("numpy"):
        item = dset[0]
        assert item.keys() == {"audio"}
        assert item["audio"].keys() == {"path", "array", "sampling_rate"}
        assert item["audio"]["path"] == audio_path
        assert item["audio"]["array"].shape == (202311,)
        assert item["audio"]["sampling_rate"] == 44100

    with dset.formatted_as("pandas"):
        item = dset[0]
        assert item.shape == (1, 1)
        assert item.columns == ["audio"]
        assert item["audio"][0].keys() == {"path", "array", "sampling_rate"}
        assert item["audio"][0]["path"] == audio_path
        assert item["audio"][0]["array"].shape == (202311,)
        assert item["audio"][0]["sampling_rate"] == 44100