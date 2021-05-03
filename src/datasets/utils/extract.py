import gzip
import lzma
import os
import shutil
import tarfile
from zipfile import ZipFile
from zipfile import is_zipfile as _is_zipfile

from datasets import config
from datasets.utils.filelock import FileLock


class TarExtractor:
    @staticmethod
    def is_extractable(path):
        return tarfile.is_tarfile(path)

    @staticmethod
    def extract(input_path, output_path):
        tar_file = tarfile.open(input_path)
        tar_file.extractall(output_path)
        tar_file.close()


class GzipExtractor:
    @staticmethod
    def is_extractable(path: str) -> bool:
        """from https://stackoverflow.com/a/60634210"""
        with gzip.open(path, "r") as fh:
            try:
                fh.read(1)
                return True
            except OSError:
                return False

    @staticmethod
    def extract(input_path, output_path):
        os.rmdir(output_path)
        with gzip.open(input_path, "rb") as gzip_file:
            with open(output_path, "wb") as extracted_file:
                shutil.copyfileobj(gzip_file, extracted_file)


class ZipExtractor:
    @staticmethod
    def is_extractable(path):
        return _is_zipfile(path)

    @staticmethod
    def extract(input_path, output_path):
        with ZipFile(input_path, "r") as zip_file:
            zip_file.extractall(output_path)
            zip_file.close()


class XzExtractor:
    @staticmethod
    def is_extractable(path: str) -> bool:
        """https://tukaani.org/xz/xz-file-format-1.0.4.txt"""
        with open(path, "rb") as f:
            try:
                header_magic_bytes = f.read(6)
            except OSError:
                return False
            if header_magic_bytes == b"\xfd7zXZ\x00":
                return True
            else:
                return False

    @staticmethod
    def extract(input_path, output_path):
        os.rmdir(output_path)
        with lzma.open(input_path) as compressed_file:
            with open(output_path, "wb") as extracted_file:
                shutil.copyfileobj(compressed_file, extracted_file)


class RarExtractor:
    @staticmethod
    def is_extractable(path: str) -> bool:
        """https://github.com/markokr/rarfile/blob/master/rarfile.py"""
        RAR_ID = b"Rar!\x1a\x07\x00"
        RAR5_ID = b"Rar!\x1a\x07\x01\x00"

        with open(path, "rb", 1024) as fd:
            buf = fd.read(len(RAR5_ID))
        if buf.startswith(RAR_ID) or buf.startswith(RAR5_ID):
            return True
        else:
            return False

    @staticmethod
    def extract(input_path, output_path):
        if config.RARFILE_AVAILABLE:
            import rarfile

            rf = rarfile.RarFile(input_path)
            rf.extractall(output_path)
            rf.close()
        else:
            raise EnvironmentError("Please pip install rarfile")


class Extractor:
    #  Put zip file to the last, b/c it is possible wrongly detected as zip (I guess it means: as tar or gzip)
    extractors = [TarExtractor, GzipExtractor, ZipExtractor, XzExtractor, RarExtractor]

    @classmethod
    def is_extractable(cls, path):
        return any(extractor.is_extractable(path) for extractor in cls.extractors)

    @classmethod
    def extract(cls, input_path, output_path):
        if not cls.is_extractable(input_path):
            raise EnvironmentError("Archive format of {} could not be identified".format(input_path))
        # Prevent parallel extractions
        lock_path = input_path + ".lock"
        with FileLock(lock_path):
            shutil.rmtree(output_path, ignore_errors=True)
            os.makedirs(output_path, exist_ok=True)
            for extractor in cls.extractors:
                if extractor.is_extractable(input_path):
                    extractor.extract(input_path, output_path)
                    break