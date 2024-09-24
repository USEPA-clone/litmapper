# LitMapper Systematic Review App

Combing through the results of a literature search can be an overwhelming process that can impede the ability of investigators to quickly ask questions, such as what articles are most similar, what emerging concepts are present that deserve closer review, and how to refine a research question. LitMapper is an open-source web application to help investigators group and explore a heterogeneous body of literature to address these needs. LitMapper provides several integrated utilities that allow users to perform text searches, cluster papers based on title and abstract text, and perform semantic network analysis that can be saved for downstream evidence synthesis.

**Tags**: information retrieval, clustering, semantic network analysis, open source

## Prerequisites

Requires [Docker](https://docs.docker.com/install/) and [docker compose](https://docs.docker.com/compose/install/).

If you're on a Mac, please ensure you've allocated at least 4GB of RAM to the Docker VM to avoid out-of-memory errors. See [the docs](https://docs.docker.com/docker-for-mac/#resources) for more info.

## Deployment

Deployment is automated via GitHub Actions.

See [the deployment README](./scripts/ci/README.md).

## Usage

Build the application images:

```bash
docker compose build
```

### Loading data from a dump

To create a dump, run the following:

```bash
./scripts/dump_database.sh
```

This will create the (gitignored) file `litmapper.pgdump` in the repository root.  You can send this file to someone else, and they can load it to bypass all the steps below.  To load a dump, move it to the root of this repository and run the following script (NOTE: it will overwrite your existing database if it's not empty):

```bash
./scripts/restore_database.sh
```

### Loading data from scratch

If you're going to be running ETL steps that access PubMed, you'll need to create a `.env` file with the following content to set needed environment variables:

```text
ENTREZ_API_KEY=<YOUR_API_KEY>
ENTREZ_EMAIL=<YOUR_EMAIL>
```

Start the application services:

```bash
docker compose up -d
```

Prepare initial input data:

- Source file (pilot data): `litmapper/etl/pilot_data.txt`

```bash
# Convert raw files to standardized format
docker compose run --rm -v <PROJECT_ROOT>/etl/:/tmp/ etl python ad_hoc/convert_pilot.py /tmp/pilot_data.csv

# Run the main data loading script
# This will not repeat steps if they've already succeeded
# and will error out if the expected initial input files haven't been created
# Will take many hours to run start to finish
./scripts/load_data.sh
```

### Adding New Articles through the App

Data can be added through the _Article Upload_ page via a CSV or a RIS file. The files must follow a specific format, shown below. An important thing to note is how the mesh terms are structured in each file type. In both, they should follow the format of `(Mesh ID 1,Mesh Term 1)|(Mesh ID 2,Mesh Term 2)`, where the data is `|`-separated tuples. An example entry might look like `(D000368,Aged)|(D015415,Biomarkers)`.

#### CSV

```CSV
id,title,abstract,mesh_terms,publication_date 
34039072,"Prognostic value of prealbumin, N-terminal pro-B-type natriuretic peptide, heart type fatty acid binding protein, and cardiac troponin I in elderly patients for heart failure and poor outcomes.","This study aimed to investigate the prognostic value of serum prealbumin, N-terminal pro-B-type natriuretic peptide (NT-proBNP), heart type fatty acid binding protein (hFABP), and cardiac troponin I (cTnI) for heart failure and cardiac death in elderly patients. We studied 426 consecutive patients with New York Heart Association classes I to IV who were recruited between February 2014 and 2018. Cardiac mortality was the primary end point. Receiver operator characteristic curves were created to analyze predictive values. When prealbumin, NT-proBNP, hFABP, and cTnI were combined, the areas under the receiver operator characteristic curve reached 0.930 and 0.903 for heart failure and cardiac death, respectively. Prealbumin, NT-proBNP, hFABP, and cTnI levels changed differently during therapy in patients in different prognosis groups. These parameters improved in patients who did not develop major adverse cardiovascular events (MACEs), but were unchanged or deteriorated in patients with MACEs. Multivariate Cox regression analysis showed that these parameters were significant independent risk factors for MACEs and cardiac death. Our study shows that serum prealbumin, NT-proBNP, hFABP, and cTnI levels are significant prognostic factors for elderly patients with poor cardiac function. These parameters are more accurate for prognosis when used together.","(D000368,Aged)|(D015415,Biomarkers)|(D006333,Heart Failure)|(D006801,Humans)|(D020097,Natriuretic Peptide, Brain)|(D010446,Peptide Fragments)|(D011228,Prealbumin)|(D011237,Predictive Value of Tests)|(D011379,Prognosis)|(D019210,Troponin I)",2021-05-27 
33907108,"False positive technetium-99m pyrophosphate scintigraphy in a patient with cardiac amyloidosis light chain: Case report.","Patients with cardiac amyloidosis light chain (AL) present with negative Tc-99m pyrophosphate (PYP) scintigraphy (absent or mild heart uptake). On the contrary, patients with cardiac amyloidosis transthyretin (ATTR) present with positive Tc-99m PYP scanning (intensive heart uptake). We present a false positive Tc-99m PYP scintigraphy (grade 2, the heart-to-contralateral ratio is 1.65) in a patient with AL. A 42-year-old Chinese man complained of effort intolerance, chest discomfort, and short of breath progressively over 1 year. New York Heart Association Class III. Physical examination showed legs swelling. Laboratory revealed elevated brain natriuretic peptide of 23,031ng/mL (0-88) and Troponin-T of 273.4ng/mL (0-14). Cardiac amyloidosis light chain. Evidences: free light chains (FLCs): decreased serum free kappa/lambda ratio of 0.043 (0.31-1.56). Immunofixation electrophoresis: a positive lambda light chain monoclonal protein. Cardiac biopsy: HE: Ambiguity Congo red strain. Myocardial immunofluorescence: positive lambda light chain. Myocardial immunohistochemistry: positive lambda light chain, negative kappa light chain, and TTR. Furosemide 40mg qd, torasemide 20mg qd, spirolactone 20mg qd, potassium chloride 10mL per 500mL urine, atorvastatin calcium tablet 20mg qd, aspirin enteric-coated tablets 100mg qd during the 2-weeks in-hospital. The patient died 2months later after discharge. False positive Tc-99m PYP scintigraphy may rarely presented in patients with cardiac amyloidosis light chain. So, the clonal plasma cell process based on the FLCs and immunofixation is a base to rule out AL cardiac amyloidosis when we interpret a positive Tc-99m PYP scintigraphy.","(D000328,Adult)|(D009202,Cardiomyopathies)|(D005189,False Positive Reactions)|(D017809,Fatal Outcome)|(D006801,Humans)|(D000075363,Immunoglobulin Light-chain Amyloidosis)|(D008297,Male)|(D011877,Radionuclide Imaging)|(D019275,Radiopharmaceuticals)|(D016698,Technetium Tc 99m Pyrophosphate)",2021-04-28
```

#### RIS

```RIS
1. 
TY  - JOUR 
ID  - 34039072 
TI  - Prognostic value of prealbumin, N-terminal pro-B-type natriuretic peptide, heart type fatty acid binding protein, and cardiac troponin I in elderly patients for heart failure and poor outcomes. 
AB  - This study aimed to investigate the prognostic value of serum prealbumin, N-terminal pro-B-type natriuretic peptide (NT-proBNP), heart type fatty acid binding protein (hFABP), and cardiac troponin I (cTnI) for heart failure and cardiac death in elderly patients. We studied 426 consecutive patients with New York Heart Association classes I to IV who were recruited between February 2014 and 2018. Cardiac mortality was the primary end point. Receiver operator characteristic curves were created to analyze predictive values. When prealbumin, NT-proBNP, hFABP, and cTnI were combined, the areas under the receiver operator characteristic curve reached 0.930 and 0.903 for heart failure and cardiac death, respectively. Prealbumin, NT-proBNP, hFABP, and cTnI levels changed differently during therapy in patients in different prognosis groups. These parameters improved in patients who did not develop major adverse cardiovascular events (MACEs), but were unchanged or deteriorated in patients with MACEs. Multivariate Cox regression analysis showed that these parameters were significant independent risk factors for MACEs and cardiac death. Our study shows that serum prealbumin, NT-proBNP, hFABP, and cTnI levels are significant prognostic factors for elderly patients with poor cardiac function. These parameters are more accurate for prognosis when used together. 
C8  - (D000368,Aged)|(D015415,Biomarkers)|(D006333,Heart Failure)|(D006801,Humans)|(D020097,Natriuretic Peptide, Brain)|(D010446,Peptide Fragments)|(D011228,Prealbumin)|(D011237,Predictive Value of Tests)|(D011379,Prognosis)|(D019210,Troponin I) 
DA  - 2021-05-27 
ER  -  

2. 
TY  - JOUR 
ID  - 32740378 
TI  - False positive technetium-99m pyrophosphate scintigraphy in a patient with cardiac amyloidosis light chain: Case report. 
AB  - Patients with cardiac amyloidosis light chain (AL) present with negative Tc-99m pyrophosphate (PYP) scintigraphy (absent or mild heart uptake). On the contrary, patients with cardiac amyloidosis transthyretin (ATTR) present with positive Tc-99m PYP scanning (intensive heart uptake). We present a false positive Tc-99m PYP scintigraphy (grade 2, the heart-to-contralateral ratio is 1.65) in a patient with AL. A 42-year-old Chinese man complained of effort intolerance, chest discomfort, and short of breath progressively over 1year. New York Heart Association Class III. Physical examination showed legs swelling. Laboratory revealed elevated brain natriuretic peptide of 23,031ng/mL (0-88) and Troponin-T of 273.4ng/mL (0-14). Cardiac amyloidosis light chain. Evidences: free light chains (FLCs): decreased serum free kappa/lambda ratio of 0.043 (0.31-1.56). Immunofixation electrophoresis: a positive lambda light chain monoclonal protein. Cardiac biopsy: HE: Ambiguity Congo red strain. Myocardial immunofluorescence: positive lambda light chain. Myocardial immunohistochemistry: positive lambda light chain, negative kappa light chain, and TTR. Furosemide 40mg qd, torasemide 20mg qd, spirolactone 20mg qd, potassium chloride 10mL per 500mL urine, atorvastatin calcium tablet 20mg qd, aspirin enteric-coated tablets 100mg qd during the 2-weeks in-hospital. The patient died 2months later after discharge. False positive Tc-99m PYP scintigraphy may rarely presented in patients with cardiac amyloidosis light chain. So, the clonal plasma cell process based on the FLCs and immunofixation is a base to rule out AL cardiac amyloidosis when we interpret a positive Tc-99m PYP scintigraphy. 
C8  - (D000328,Adult)|(D009202,Cardiomyopathies)|(D005189,False Positive Reactions)|(D017809,Fatal Outcome)|(D006801,Humans)|(D000075363,Immunoglobulin Light-chain Amyloidosis)|(D008297,Male)|(D011877,Radionuclide Imaging)|(D019275,Radiopharmaceuticals)|(D016698,Technetium Tc 99m Pyrophosphate) 
DA  - 2021-04-28 
ER  - 
```

### Manually Adding New Articles

#### Create the new data file

To add new data to the app, first save a new `.csv` file in the `etl/data` subfolder. A template data file `add_pubmed_template.csv` is saved in `etl/data` for convenience. The data should be in the format:

```text
PMID,tag_name,tag_value,requester,upload_date
<PMID>,source,User Request,<Scientist Name>,<Date in YYYY-MM-DD format>
```

#### Run the add data script

Unlike the load data script, `add_data.sh` only generates and uploads tags, embeddings, and chemicals for the articles included in the data file, rather than conducting these processes for the entire article corpus.

Run the add data script followed by the name of the `.csv` file saved in `etl/data` to add the new articles to the db:

```bash
./scripts/add_data.sh <data_file_name>
```

If we were using the template file:

```bash
./scripts/add_data.sh add_pubmed_template.csv
```

#### Checkpoints and Database Backup

Like the load data script, `add_data.sh` creates checkpoints to save progress as it runs. Be sure to remove the `articles_tags`, `chemicals`, and `embeddings` checkpoints from `etl/data/.ckpt-add-data` when adding a new batch of data to the database.

The `add_data.sh` script also creates a dump to archive the database's state _before_ the new articles are added to the corpus. The backup is saved in the `etl/data/.ckpt-add-data` folder using the following format for the filename:

```text
litmapper_2024_MM_DD_HH_MM.pgdump
```

In the event of an emergency, move this file into the project root directory, rename it `litmapper.pgdump`, and run `./scripts/restore_database.sh` to restore the database to its state just before `add_data.sh` was run. These dumps are large files and should be deleted periodically.

## Development

Access the website at [http://localhost:8080](http://localhost:8080).  You can access the API directly at [http://localhost:8000](http://localhost:8000), and the API docs are at [http://localhost:8000/docs](http://localhost:8000/docs).

### Backend

See [the FastAPI SQL DB tutorial](https://fastapi.tiangolo.com/tutorial/sql-databases/) for the source of the high-level API/DB access design.

To create a new database migration, modify `backend/litmapper/models.py` and run the following:

```bash
./scripts/create_migration.sh -m "<migration_name>"
```

Edit the new migration if needed.  To run migrations, run:

```bash
./scripts/migrate.sh
```

If you need to revert migrations or otherwise run alembic commands, pass extra arguments to `scripts/migrate.sh` -- they'll be passed directly to the `alembic` command.  Ex:

```bash
./scripts/migrate.sh downgrade -1
```

To run linters, run:

```bash
./scripts/lint_backend.sh
```

Enable black/isort/mypy/flake8 in your editor to catch issues more quickly.

To run tests, make sure required containers are up and running with `docker compose up -d`, then run:

```bash
./scripts/test_backend.sh
```

Note additional arguments are passed directly to `py.test`.  If you want to preserve the test database (`litmapper_test`) between test runs, use:

```bash
./scripts/test_backend.sh --keep-db --force-db
```

#### Backend Code Structure

The `litmapper` directory contains all the code for the Python package composing the backend API.  Here's what's under each subdirectory:

- `alembic/`: [alembic](https://alembic.sqlalchemy.org/en/latest/) configuration and migrations for synchronizing the database schema.  Prefer creating and running these using the scripts referenced above, but they're here if you need to edit them manually.
- `db/`: Utility functions and code for interaction with the main relational database managed by SQLAlchemy and alembic.  There's a module here for each router group.
- `errors.py`: Common error classes used across the app.
- `kv/`: Utility functions and code for interaction with the auxiliary key-value store, used for application-level caching of certain objects at runtime.  There's a module here for each router group.
- `main.py`: Main entrypoint for the app.
- `models.py`: [SQLAlchemy](https://www.sqlalchemy.org/) models for the app -- used to access data in the database.
- `routers/`: [FastAPI](https://fastapi.tiangolo.com/) routes for the app.  There's a module here for each router group.
- `schemas.py`: [Pydantic](https://pydantic-docs.helpmanual.io/) models used for shared data representation across the app.  These are used as a bridge between incoming/outgoing data for the FastAPI routes and storage in the database/key-value store.
- `tasks.py`: Background tasks designed to be run in a separate worker process using [dramatiq](https://dramatiq.io/).  These correspond to time-consuming database queries/algorithms and other operations that shouldn't be run in the main FastAPI process.
- `test/`: Tests for all modules in the app.

### ETL

To run linters, run:

```bash
./scripts/lint_etl.sh
```

Enable black/isort/mypy/flake8 in your editor to catch issues more quickly.

### Frontend

To run linters, run:

```bash
./scripts/lint_frontend.sh
```

Enable prettier/eslint in your editor to catch issues more quickly.

### Specter Embeddings

A separate database is run to hold articles' specter embeddings. To initialize this database, run:

```bash
./scripts/specter_init_database.sh
```

To populate this database with embeddings, create a `.csv` file with the following columns in the `/specter/data/` directory: `article_id`, `embedding`. For reference, an example `.csv` file is located at `/specter/data/example_embeddings.csv`.

To run the script to populate:

```bash
    ./scripts/specter_populate_database.sh`<filename>`.csv
```

For example:

```bash
    ./scripts/specter_populate_database.sh example_embeddings.csv
```

## Disclaimer

The United States Environmental Protection Agency (EPA) GitHub project
code is provided on an "as is" basis and the user assumes responsibility for its use. EPA
has relinquished control of the information and no longer has responsibility to protect
the integrity, confidentiality, or availability of the information. Any reference to specific
commercial products, processes, or services by service mark, trademark, manufacturer, or
otherwise, does not constitute or imply their endorsement, recommendation or favoring
by EPA. The EPA seal and logo shall not be used in any manner to imply endorsement of
any commercial product or activity by EPA or the United States Government.

## Contact

If you have any questions, please reach out to Scott Lynn at <Lynn.Scott@epa.gov>
