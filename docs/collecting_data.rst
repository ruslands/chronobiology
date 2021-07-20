Storing and collecting data for analysis
========================================

Input data is represented by a stack of arrays containing the following data:

    * timestamps of measurements,

    * measured actity values,

    * time of day for each measurement (night or day).

These arrays must be loaded manually from any existing file, database or server.

We recommend **InfluxDB** to store the analyzed data.
The package provides class :class:`~chronobiology.chronobiology.DBQuery` to connect to
your InfluxDB databases and read data from them.

.. toctree::
    demos/db_query
