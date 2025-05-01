# Run Datasette

This directory has the information used to run Datasette for tables

## To use

Create a virtual environment and install `requirements.txt`.

You need a SQLite database. Either download a real one from tables to `iati.db` or run:

    sqlite3 iati.db "CREATE TABLE nodatayet(id INTEGER)"

Run:

    cp templates/base.template.html templates/base.html
    datasette -i iati.db --template-dir=templates

## Why base_with_variables.template.html?

On the server our deploy scripts will copy base.template.html to base.html and then edit TABLES.DOMAIN.EXAMPLE.COM to the real domain.

This makes sure we set the domain correctly on the live server, any test servers and that we don't mix dev traffic in with live.



