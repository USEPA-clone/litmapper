FROM python:3.9

COPY ./setup.py /code/

RUN apt-get update && apt-get install -y libhdf5-dev

WORKDIR /code
# Cython and numpy needed for jqm_cvi package
RUN pip install --upgrade pip==23.3.2 \
    && pip install Cython==0.29.37 numpy==1.26.4 \
    && pip install -e '.[dev]'
RUN python -c 'import tensorflow_hub as hub; hub.load("https://tfhub.dev/google/universal-sentence-encoder/4")'

EXPOSE 8000
CMD ["uvicorn", "--host", "0.0.0.0", "--reload", "--reload-dir", "/code/litmapper", "litmapper.main:app"]
