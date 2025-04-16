=======
Process
=======

Data Retrieval
--------------

IATI Tables retrieves data from the `Code for IATI Data Dump <https://iati-data-dump.codeforiati.org/>`_ once a day.
All data is replaced each time the process runs, so updates and removals are respected.

You can use the `metadata table <https://datasette.codeforiati.org/iati/metadata>`_ to find the cut-off time for the data which is included.
The column :code:`iati_tables_updated_at` shows the time at which the tables process finished.
The column :code:`data_dump_updated_at` shows the time of the Data Dump that was used by the latest run.
IATI data published or edited after this time will not be included in IATI Tables until the next run.

Flattening
----------

Top-level elements
++++++++++++++++++

There are two top-level tables in IATI Tables:

1. The :code:`activity` table is generated from `Activity <https://iatistandard.org/en/iati-standard/203/activity-standard/>`_ files, and contains rows of :iati-reference:`iati-activities/iati-activity` elements.
2. The :code:`organisation` table is generated from `Organisation <https://iatistandard.org/en/iati-standard/203/organisation-standard/>`_ files, and contains rows of :iati-reference:`iati-organisations/iati-organisation` elements.

All other tables are children of these top-level tables.
Tables prefixed with :code:`organisation_` contain child elements of the :iati-reference:`iati-organisations/iati-organisation` element, and can be joined back to the :code:`organisation` table using the column :code:`_link_organisation`.
The remaining tables contain child elements of the :iati-reference:`iati-activities/iati-activity` element, and can be joined back to the :code:`activity` table using the column :code:`_link_activity`.

.. note::
  **IATI Tables doesn't perform deduplication.** If an activity appears multiple times in published data, it will appear multiple times in IATI tables.

Singular child elements
+++++++++++++++++++++++

Child elements which can appear zero or one times become columns in the parent table.

For example, the :iati-reference:`iati-activities/iati-activity/iati-identifier` element becomes the column :code:`iati-identifier` in the :code:`activity` table.

Repeatable child elements
+++++++++++++++++++++++++

Child elements which can appear more than once are unnested into a new table.

For example, the :iati-reference:`iati-activities/iati-activity/transaction` element becomes the table :code:`transaction`.

Narrative elements
++++++++++++++++++

Elements which contain a :code:`narrative` element are flattened into a single string column in the parent table.

For example, given the following :iati-reference:`iati-activities/iati-activity/title` element:

.. code:: xml

  <title>
    <narrative>Activity title</narrative>
    <narrative xml:lang="fr">Titre de l'activité</narrative>
    <narrative xml:lang="es">Título de la actividad</narrative>
  </title>

This element will be transformed into the string: :code:`Activity title, FR: Titre de l'activité, ES: Título de la actividad`,
and stored in the column :code:`title_narrative` in the :code:`activity` table.

Common columns
++++++++++++++

The following columns are present in all tables:

:code:`_link`
  The primary key for each table.
:code:`_link_activity` or :code:`_link_organisation`
  The foreign key to the :code:`activity` or :code:`organisation` table respectively.
:code:`dataset`
  The name of the dataset this row came from. This can be used to find the dataset in the IATI registry, using the URL: :code:`https://www.iatiregistry.org/dataset/<DATASET_NAME>`.
:code:`prefix`
  The registry publisher ID this row came from. This can be used to find the dataset in the IATI registry, using the URL: :code:`https://www.iatiregistry.org/publisher/<PREFIX>`.

Codelists
---------

Codelists are joined to the tables as part of the process.

For example, given the following :iati-reference:`iati-activities/iati-activity/activity-status` element,
whose attribute :code:`@code` uses the `ActivityStatus <https://iatistandard.org/en/iati-standard/203/codelists/ActivityStatus/>`_ codelist:

.. code:: xml

  <activity-status code="2" />

This element will be transformed into two columns in the :code:`activity` table:

- The column :code:`activitystatus_code` with the value :code:`2`.
- The column :code:`activitystatus_codename` with the value :code:`Implementation`.

Currency Conversion
-------------------

.. TODO: https://github.com/codeforIATI/imf-exchangerates

Transaction Breakdown
---------------------

.. TODO: https://countrydata.iatistandard.org/methodology/#24-splitting-transactions-for-multiple-sectors-and-countries
