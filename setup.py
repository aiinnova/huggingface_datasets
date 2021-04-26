# Lint as: python3
""" HuggingFace/Datasets is an open library of NLP datasets.

Note:

   VERSION needs to be formatted following the MAJOR.MINOR.PATCH convention
   (we need to follow this convention to be able to retrieve versioned scripts)

Simple check list for release from AllenNLP repo: https://github.com/allenai/allennlp/blob/master/setup.py

To create the package for pypi.

1. Change the version in __init__.py, setup.py as well as docs/source/conf.py.

2. Commit these changes with the message: "Release: VERSION"

3. Add a tag in git to mark the release: "git tag VERSION -m'Adds tag VERSION for pypi' "
   Push the tag to git: git push --tags origin master

4. Build both the sources and the wheel. Do not change anything in setup.py between
   creating the wheel and the source distribution (obviously).

   For the wheel, run: "python setup.py bdist_wheel" in the top level directory.
   (this will build a wheel for the python version you use to build it).

   For the sources, run: "python setup.py sdist"
   You should now have a /dist directory with both .whl and .tar.gz source versions.

5. Check that everything looks correct by uploading the package to the pypi test server:

   twine upload dist/* -r pypitest
   (pypi suggest using twine as other methods upload files via plaintext.)
   You may have to specify the repository url, use the following command then:
   twine upload dist/* -r pypitest --repository-url=https://test.pypi.org/legacy/

   Check that you can install it in a virtualenv by running:
   pip install -i https://testpypi.python.org/pypi datasets

6. Upload the final version to actual pypi:
   twine upload dist/* -r pypi

7. Fill release notes in the tag in github once everything is looking hunky-dory.

8. Update the documentation commit in .circleci/deploy.sh for the accurate documentation to be displayed
   Update the version mapping in docs/source/_static/js/custom.js,
   and set version to X.X.X.dev0 in setup.py and __init__.py

"""

import datetime
import itertools
import os
import sys

from setuptools import find_packages, setup


DOCLINES = __doc__.split("\n")


# Pin some dependencies for old python versions
_deps = {
    "fsspec": "fsspec"
    if sys.version_info >= (3, 7)
    else "fsspec<0.8.1",  # fsspec>=0.8.1 requires py>=3.7 for async stuff
    "s3fs": "s3fs"
    if sys.version_info >= (3, 7)
    else "s3fs==0.4.2",  # later versions of s3fs have issues downloading directories recursively for py36
}


REQUIRED_PKGS = [
    # We use numpy>=1.17 to have np.random.Generator (Dataset shuffling)
    "numpy>=1.17",
    # Backend and serialization.
    # Minimum 1.0.0 to avoid permission errors on windows when using the compute layer on memory mapped data
    "pyarrow>=1.0.0",
    # For smart caching dataset processing
    "dill",
    # For performance gains with apache arrow
    "pandas",
    # for downloading datasets over HTTPS
    "requests>=2.19.0",
    # progress bars in download and scripts
    # tqdm 4.50.0 introduced permission errors on windows
    # see https://app.circleci.com/pipelines/github/huggingface/datasets/235/workflows/cfb6a39f-68eb-4802-8b17-2cd5e8ea7369/jobs/1111
    "tqdm>=4.27,<4.50.0",
    # dataclasses for Python versions that don't have it
    "dataclasses;python_version<'3.7'",
    # for fast hashing
    "xxhash",
    # for better multiprocessing
    "multiprocess",
    # to get metadata of optional dependencies such as torch or tensorflow for Python versions that don't have it
    "importlib_metadata;python_version<'3.8'",
    # to save datasets locally or on any filesystem
    _deps["fsspec"],
    # To get datasets from the Datasets Hub on huggingface.co
    "huggingface_hub<0.1.0",
    # Utilities from PyPA to e.g., compare versions
    "packaging",
]

BENCHMARKS_REQUIRE = [
    "numpy==1.18.5",
    "tensorflow==2.3.0",
    "torch==1.6.0",
    "transformers==3.0.2",
]

TESTS_REQUIRE = [
    # test dependencies
    "absl-py",
    "pytest",
    "pytest-xdist",
    # optional dependencies
    "apache-beam>=2.26.0",
    "elasticsearch",
    "aiobotocore==1.2.2",
    "boto3==1.16.43",
    "botocore==1.19.52",
    "faiss-cpu",
    "fsspec[s3]",
    "moto[s3,server]==2.0.4",
    "rarfile>=4.0",
    _deps["s3fs"],
    "tensorflow>=2.3",
    "torch",
    "transformers",
    # datasets dependencies
    "bs4",
    "conllu",
    "langdetect",
    "lxml",
    "mwparserfromhell",
    "nltk",
    "openpyxl",
    "py7zr",
    "tldextract",
    "zstandard",
    # metrics dependencies
    "bert_score>=0.3.6",
    "rouge_score",
    "sacrebleu",
    "scipy",
    "seqeval",
    "sklearn",
    "jiwer",
    "sentencepiece",  # for bleurt
    # to speed up pip backtracking
    "toml>=0.10.1",
    "requests_file>=1.5.1",
    "tldextract>=3.1.0",
    "texttable>=1.6.3",
    "Werkzeug>=1.0.1",
    # metadata validation
    "importlib_resources;python_version<'3.7'",
]

if os.name == "nt":  # windows
    TESTS_REQUIRE.remove("faiss-cpu")  # faiss doesn't exist on windows
else:
    # dependencies of unbabel-comet
    # only test if not on windows since there're issues installing fairseq on windows
    TESTS_REQUIRE.extend(
        [
            "wget>=3.2",
            "pytorch-nlp==0.5.0",
            "pytorch_lightning",
            "fastBPE==0.1.0",
            "fairseq",
        ]
    )


QUALITY_REQUIRE = ["black>=21.4b0", "flake8==3.7.9", "isort", "pyyaml>=5.3.1"]


EXTRAS_REQUIRE = {
    "apache-beam": ["apache-beam>=2.26.0"],
    "tensorflow": ["tensorflow>=2.2.0"],
    "tensorflow_gpu": ["tensorflow-gpu>=2.2.0"],
    "torch": ["torch"],
    "s3": [
        _deps["fsspec"],
        "boto3==1.16.43",
        "botocore==1.19.52",
        _deps["s3fs"],
    ],
    "dev": TESTS_REQUIRE + QUALITY_REQUIRE,
    "tests": TESTS_REQUIRE,
    "quality": QUALITY_REQUIRE,
    "benchmarks": BENCHMARKS_REQUIRE,
    "docs": [
        "docutils==0.16.0",
        "recommonmark",
        "sphinx==3.1.2",
        "sphinx-markdown-tables",
        "sphinx-rtd-theme==0.4.3",
        "sphinxext-opengraph==0.4.1",
        "sphinx-copybutton",
        _deps["fsspec"],
        _deps["s3fs"],
    ],
}

setup(
    name="datasets",
    version="1.6.0.dev0",  # expected format is one of x.y.z.dev0, or x.y.z.rc1 or x.y.z (no to dashes, yes to dots)
    description=DOCLINES[0],
    long_description="\n".join(DOCLINES[2:]),
    author="HuggingFace Inc.",
    author_email="thomas@huggingface.co",
    url="https://github.com/huggingface/datasets",
    download_url="https://github.com/huggingface/datasets/tags",
    license="Apache 2.0",
    package_dir={"": "src"},
    packages=find_packages("src"),
    package_data={"datasets": ["scripts/templates/*"], "datasets.utils.resources": ["*.json"]},
    entry_points={"console_scripts": ["datasets-cli=datasets.commands.datasets_cli:main"]},
    install_requires=REQUIRED_PKGS,
    extras_require=EXTRAS_REQUIRE,
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Education",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    keywords="datasets machine learning datasets metrics",
)
