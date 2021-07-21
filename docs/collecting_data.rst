Storing and collecting data for analysis
========================================

Activity data collected during an experiment is usually represented by a stack of arrays
of equal length containing the following data:

* **timestamps of activity measurements** -- each timestamp represents the time of a certain measurement;

* **measured actity values** -- values obtained by a sensor (represented by real or integer positive numbers);

* **Time of day (night or day)** -- boolean array with true values standing for nighttime measurements and false values standing for daytime measurements.

These arrays must be loaded manually from any existing file, database or server.

We recommend **InfluxDB** to store activity data.
This package provides class :class:`~chronobiology.chronobiology.DBQuery` to connect to
your InfluxDB and read data from it.

Each searies of measurements should be represented by a separate InfluxDB table with the following columns:

* **time** -- timestamps of measurements (used as the main index);

* **value** -- numeric values obtained by sensors;

* **sensor_id** -- sensor identifier (in case of multiple sensors);

* **is_night** -- day/night marker;

* other additional columns for indexing and filtering purpuses if needed.

In InfluxDB, columns can be fields or tags. Tags are more efficient to construct WHERE-queries but
they can hold only string data. So it's better to have **value** and **is_night** stored
as fields and **sensor_id** stored as a tag.

.. toctree::
    demos/db_query
