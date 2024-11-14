FROM python:3.9

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install -r /code/requirements.txt
CMD ["../usr/bin/python3", "./populate.py"]
