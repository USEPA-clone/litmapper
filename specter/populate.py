import pandas as pd
import os
from sqlalchemy import create_engine
import sys

specter_file = (sys.argv[1])

url = os.environ["POSTGRES_URI"]
engine = create_engine(url)

cols = ["article_id", "embedding"]

chunksize = 20000
for chunk in pd.read_csv(f"data/{specter_file}", chunksize=chunksize, iterator=True, usecols=cols):
    chunk.to_sql("specter", engine, if_exists="append", index=False)
