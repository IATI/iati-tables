# IATI Tables

IATI Tables transforms IATI data into relational tables.

To access the data please go to the [website](https://iati-tables.codeforiati.org/) and for more information on how to use the data please see the [documentation site](https://docs.tables.iatistandard.org/).

## How to run the processing job

The processing job is a Python application which downloads the data from the [IATI Data Dump](https://iati-data-dump.codeforiati.org/), transforms the data into tables, and outputs the data in various formats such as CSV, PostgreSQL and SQLite. It is a batch job, designed to be run on a schedule.

### Prerequisites

- postgresql 14
- sqlite
- zip

### Install Python requirements

```
python3 -m venv .ve
source .ve/bin/activate
pip install pip-tools
pip-sync requirements_dev.txt
```

### Set up the PostgreSQL database

Create user `iatitables`:

```
sudo -u postgres psql -c "create user iatitables with password 'PASSWORD_CHANGEME'"
```

Create database `iatitables`

```
sudo -u postgres psql -c "create database iatitables encoding utf8 owner iatitables"
```

Set `DATABASE_URL` environment variable

```
export DATABASE_URL="postgresql://iatitables:PASSWORD_CHANGEME@localhost/iatitables"
```

### Configure the processing job

The processing job can be configured using the following environment variables:

`DATABASE_URL` (Required)

- The postgres database to use for the processing job.

`IATI_TABLES_OUTPUT` (Optional)

- The path to output data to. The default is the directory that IATI Tables is run from.

`IATI_TABLES_SCHEMA` (Optional)

- The schema to use in the postgres database.

`IATI_TABLES_S3_DESTINATION` (Optional)

- By default, IATI Tables will output local files in various formats, e.g. pg_dump, sqlite, and CSV. To additionally upload files to S3, set the environment variable `IATI_TABLES_S3_DESTINATION` with the path to your S3 bucket, e.g. `s3://my_bucket`.

### Run the processing job

```
python -c 'import iati_tables; iati_tables.run_all(processes=6, sample=50, refresh=False)'
```

Parameters:

- `processes` (`int`, default=`5`): The number of workers to use for parts of the process which are able to run in parallel.
- `sample` (`int`, default=`None`): The number of datasets to process. This is useful for local development because processing the entire data dump can take several hours to run. A minimum sample size of 50 is recommended due to needing enough data to dynamically create all required tables (see https://github.com/codeforIATI/iati-tables/issues/10).
- `refresh` (`bool`, default=`True`): Whether to download the latest data at the start of the processing job. It is useful to set this to `False` when running locally to avoid re-downloading the data every time the process is run.

## How to run linting and formatting

```
isort iati_tables/ tests/
black iati_tables/ tests/
flake8 iati_tables/ tests/
mypy iati_tables/ tests/
```

## Run unit and integration tests

In one terminal:

```
docker compose -f tests/docker-compose.yml up -d --wait
pytest
docker compose -f tests/docker-compose.yml down
```

To run pytest with coverage, use the following command:

```
pytest --cov --cov-report=html:coverage
```

Then open `coverage/index.html` in your browser to view results.

## How to run the web front-end

### Prerequisites:

- Node.js v20

Change the working directory:

```
cd site
```

Install dependencies:

```
yarn install
```

Start the development server:

```
yarn serve
```

Or, build and view the site in production mode (http.server is not suitable for actual production):

```
yarn build
cd site/dist
python3 -m http.server --bind 127.0.0.1 8000
```

## How to run the documentation

The documentation site is built with Sphinx. To view the live preview locally, run the following command:

```
sphinx-autobuild docs docs/_build/html
```

# How to run Datasette

You need a SQLite database with the name `iati.sqlite`. Either: 

* Download a real one from tables
* Run the pipeline locally in sample mode
* Run `sqlite3 iati.sqlite "CREATE TABLE nodatayet(id INTEGER)"`

To run datasette as a local server, run:

    cp datasette/templates/base.template.html datasette/templates/base.html
    datasette -i iati.sqlite --template-dir=datasette/templates --static iatistatic:datasette/static

## Why base.template.html?

On the server our deploy scripts will copy base.template.html to base.html and then edit TABLES.DOMAIN.EXAMPLE.COM to the real domain.

This makes sure we set the domain correctly on the live server and any test servers and that we don't mix dev traffic in with live.



