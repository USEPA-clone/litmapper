from setuptools import find_packages, setup

setup(
    name="litmapper",
    packages=find_packages(exclude=["test"]),
    include_package_data=True,
    install_requires=[
        "fastapi==0.112.1",
        "uvicorn==0.30.6",
        "gunicorn==22.0.0",
        "SQLAlchemy==1.3.13",
        "alembic==1.4.0",
        "psycopg2-binary==2.9.9",
        "pydantic==1.10.14",
        "SQLAlchemy-Utils==0.36.1",
        "pandas==1.5",
        "spacy==2.3.9",
        "hdbscan==0.8.33",
        "umap-learn==0.5.3",
        "numba==0.57.1",
        "llvmlite==0.40.1",
        "scipy==1.11.1",
        "scikit-learn==1.5.0",
        "en_core_sci_md @ https://s3-us-west-2.amazonaws.com/ai2-s2-scispacy/releases/v0.3.0/en_core_sci_md-0.3.0.tar.gz",
        # Note: this package requires Cython and numpy build dependencies but doesn't
        # specify them in its dependencies, so they must be installed manually before installing
        # this package
        "jqmcvi @ git+https://github.com/hardingalexh/jqm_cvi.git",
        # Needed for FastAPI on Python 3.6
        "async-exit-stack==1.0.1",
        "async_generator==1.10",
        "redis==3.5.3",
        "hiredis==1.0.1",
        "dramatiq[rabbitmq,watch,redis]==1.9.0",
        "keras==2.14.0",
        "tensorflow_hub==0.14.0",
        "colorcet==2.0.2",
        "SQLAlchemy-Searchable==1.2.0",
        "prefect==0.15.13",
        "biopython==1.79",
        "absl-py",
        "tensorflow==2.14.0",
        "rispy==0.8.1",
        "thefuzz==0.22.1",
        "python-multipart==0.0.9",
    ],
    extras_require={
        "dev": [
            "pytest==5.3.5",
            "pytest-sugar==0.9.4",
            "black==24.3.0",
            "flake8==3.7.9",
            "isort==4.3.21",
            "mypy==1.0.1",
            "sqlalchemy-stubs==0.3",
            "requests==2.31.0",
            # Needed for mypy
            "types-redis==3.5.3",
            "types-requests==2.31.0",
            "httpx==0.27.2"
        ]
    },
)
