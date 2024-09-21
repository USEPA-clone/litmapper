import datetime as dt

from Bio import Entrez
from prefect import task

from .secret import get_entrez_api_key, get_entrez_email


@task
def search_articles_count(term):
    Entrez.email = get_entrez_email().run()
    handle = Entrez.esearch(db="pubmed", retmax=100000, term=term)
    record = Entrez.read(handle)
    handle.close()

    return {
        "count": int(record["Count"]),
        "pmids": [int(pmid) for pmid in record["IdList"]],
    }


# if needed for future use
@task(max_retries=5, retry_delay=dt.timedelta(minutes=5))
def search_articles(term):
    Entrez.email = get_entrez_email().run()
    Entrez.api_key = get_entrez_api_key().run()

    retstart = 0
    res_count = int(search_articles_count.run(term))
    res = []

    while res_count > retstart:
        handle = Entrez.esearch(
            db="pubmed", retstart=retstart, retmax=100000, term=term
        )
        record = Entrez.read(handle)
        handle.close()
        res += record["IdList"]

        retstart += 100000

    return res


@task
def search_pumbed_ids(ids: list[int]):
    Entrez.email = get_entrez_email().run()
    Entrez.api_key = get_entrez_api_key().run()
    id_str = ",".join([str(id) for id in ids])
    handle = Entrez.esummary(db="pubmed", retmax=100000, id=id_str)
    records = Entrez.read(handle)
    handle.close()

    return [{"id": int(record["Id"]), "title": record["Title"]} for record in records]
