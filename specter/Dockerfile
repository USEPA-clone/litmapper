FROM python:3.9

WORKDIR /code
COPY . /code
COPY ./requirements.txt /code/requirements.txt
RUN ls -la
RUN pip install -r /code/requirements.txt
RUN chmod +x populate.py
CMD ["../usr/bin/python3", "./populate.py"]


