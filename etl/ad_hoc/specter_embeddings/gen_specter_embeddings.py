"""
Left in repo for documentation. Process to generate specter embeddings
from a list of articles pulled from the database. For best results,
run this script on a GPU.
"""

import pandas as pd
from transformers import AutoModel, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("allenai/specter")
model = AutoModel.from_pretrained("allenai/specter")

articles_array = pd.read_csv(
    "./ad_hoc/specter_embeddings/articles_csv_example.csv"
).to_dict(orient="records")


def format_article(article):
    return f"{article['title']}\n{article['abstract']}"


def gen_embeds(article_array):
    formatted_arts = [format_article(a) for a in article_array]
    article_ids = [a["article_id"] for a in article_array]

    # Separate title_abs into article chunks to prevent OOM issues
    chunk_size = 3
    chunks = [
        formatted_arts[x : x + chunk_size]
        for x in range(0, len(formatted_arts), chunk_size)
    ]

    # Create embeddings
    all_embeds = []
    for chunk in chunks:
        inputs = tokenizer(
            chunk,
            padding=True,
            truncation=True,
            return_tensors="pt",
            max_length=512,
        )
        result = model(**inputs)
        chunk_embeds = result.last_hidden_state[:, 0, :].tolist()
        all_embeds = all_embeds + chunk_embeds
    return dict(zip(article_ids, all_embeds))


embeddings_table = gen_embeds(articles_array)
out_df = pd.DataFrame(
    {"article_id": embeddings_table.keys(), "embedding": embeddings_table.values()}
)
out_df.to_csv("./ad_hoc/specter_embeddings/embedding_output_example.csv")
