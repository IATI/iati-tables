==============
Output Formats
==============

Datasette
=========

`Datasette <https://datasette.io/>`_ is an open source tool for exploring data.
The `IATI Tables Datasette <https://datasette.codeforiati.org/>`_ instance allows you to explore IATI data in the browser using SQL, as well as download the results of your query in multiple formats.
For more information please see the `Datasette documentation <https://docs.datasette.io/en/stable/>`_.

CSV Zip
=======

The CSV Zip file contains a compressed folder containing a CSV file for each table, which you can explore by importing into a spreadsheet viewer such as Excel or Google Sheets.
For more information, please see :ref:`Spreadsheets`.

SQLite Zip
==========

The SQLite Zip file is a compressed `SQLite <https://www.sqlite.org/>`_ database, which can be run and explored with :code:`sqlite3`.

PG Dump
=======

The PG Dump files can be loaded into a `PostgreSQL <https://www.postgresql.org/>`_ database and are created by the `pg_dump <https://www.postgresql.org/docs/current/app-pgdump.html>`_ utility.

There are two options to choose from, gzip or custom:

Gzip
----

The 'gzip' format gives you a compressed plaintext script of SQL commands, which can be restored using :code:`psql`.

Custom
------

The 'custom' format can be restored using the `pg_restore <https://www.postgresql.org/docs/current/app-pgrestore.html>`_ utility.
This option is more flexible if you want to perform any schema changes before restoring.

Colab Notebook
==============

The `Google Colab <https://colab.research.google.com/drive/15Ahauin2YgloaFEwiGjqbnv7L91xNUua>`_ notebook, shows some examples of how the data can be explored in Jupyter Notebook format.
You can save a copy of the notebook to edit it for your own use case.
