"""
Convert from the Kiros literature search results file to a standardized
format which can more easily be loaded by our ETL script, containing PMIDs, tag names,
and tag values.

Original filename: DocumentList.txt (also referencing various nearby folders named for endpoints)
"""

from pathlib import Path

import click
import pandas as pd

data_dir = Path(__file__).parent.parent / "data"


@click.command("main")
@click.argument("input_filepath")
def main(input_filepath: str):
    tag_df = pd.read_csv(
        input_filepath, usecols=["RefID", "Author", "Title", "Abstract"]
    )
    tag_df = tag_df.rename({"RefID": "PMID"}, axis=1)

    output_path = data_dir / "pilot.csv"
    tag_df.to_csv(output_path, index=False)
    print(f"Data written to {output_path}")


if __name__ == "__main__":
    main()
