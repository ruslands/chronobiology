from pathlib import Path
from datetime import datetime, timedelta, tzinfo, timezone
from itertools import *

from influxdb import InfluxDBClient, DataFrameClient
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections.abc import Sequence
from scipy import integrate


class DBQuery():
    """Class to access InfluxDB 1.x and get records from it.
    
    Initialization:
    --------------------------------------------------------------------------------
    DBQuery(database, username, password, host='localhost', port=8086)
    * database: Name of the database, string.
    * username: Name of user, string.
    * password: User password, string.
    * host: IP adress, string. Optional.
    * port: Connection port, int. Optional.
    
    Methods:
    --------------------------------------------------------------------------------
    * get_measurements: Get list of measurements (series) in DB
    * get_tags: Get list of tags in the series
    * get_fields: Get list of fields in the series (optionally return their types)
    * get_keys: Get list of keys (tag values) for the given tag in the series
    * get_data: Get data for the specified fields/values from series and return it
      as dict of columns.
    
    Usage examples:
    --------------------------------------------------------------------------------
    
    q = DBQuery("MyDatabase", "user", "password", host="186.12.1.4", port=8000)
    
    # Get list of measurements (series)
    q.get_measurements()
    >> ['series1', 'series2', 'series_with_no_tags']
    
    # Get list of tags
    q.get_tags('series1')
    >> ['tag1', 'tag2']
    
    # Get list of fields
    q.get_fields('series1', return_types=False)
    >> ['value']
    
    # Get list of fields and their types
    q.get_fields('series1', return_types=True)
    >> (['value'], ['integer'])
    
    # Get list of tag values (keys)
    q.get_keys('series1', 'tag1')
    >> ['foo', 'bar']
    
    # Get data
    
    # Use '*' to select all fields/tags
    q.get_data('series1', '*')
    >> {'time': array(['2019-11-05T00:00:00.000000000', 
    ...                '2019-11-05T06:00:00.000000000', 
    ...                '2019-11-06T00:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'tag1': array(['foo', 'bar', 'foo'], dtype='<U3'),
    ... 'tag2': array(['1', '2', '3'], dtype='<U1'),
    ... 'value': array([1.0, 1.5, 2.0], dtype=float64)}
    
    # start is inclusive
    q.get_data('series1', 'value', start='2019-11-05 06:00')
    >> {'time': array(['2019-11-05T06:00:00.000000000', 
    ...                '2019-11-06T00:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'value': array([1.5, 2.0], dtype=float64)}
    
    # stop is exclusive
    q.get_data('series1', ['value', 'tag1'], stop='2019-11-06')
    >> {'time': array(['2019-11-05T00:00:00.000000000', 
    ...                '2019-11-05T06:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'value': array([1.0, 1.5], dtype=float64),
    ... 'tag1': array(['foo', 'bar'], dtype='<U3')}
    
    # Specify key value
    q.get_data('series1', '*', {'tag1': 'foo'})
    >> {'time': array(['2019-11-05T00:00:00.000000000', 
    ...                '2019-11-06T00:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'tag1': array(['foo', 'foo'], dtype='<U3'),
    ... 'tag2': array(['1', '3'], dtype='<U1'),
    ... 'value': array([1.0, 2.0], dtype=float64)}
    
    # Specify multiple values for one key and use autoconversion to string
    q.get_data('series1', 'value', {'tag2': [1, 2]})
    >> {'time': array(['2019-11-05T00:00:00.000000000', 
    ...                '2019-11-05T06:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'tag1': array(['foo', 'bar'], dtype='<U3'),
    ... 'tag2': array(['1', '2'], dtype='<U1'),
    ... 'value': array([1.0, 1.5], dtype=float64)}
    
    # Specify multiple keys
    q.get_data('series1', 'value', {'tag1': 'foo', 'tag2': [1, 2]})
    >> {'time': array(['2019-11-05T00:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'tag1': array(['foo'], dtype='<U3'),
    ... 'tag2': array(['1'], dtype='<U1'),
    ... 'value': array([1.0], dtype=float64)}
    """
    
    def __init__(self, database, username, password, host='localhost', port=8086):
        self.database = database
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.client = InfluxDBClient(host=self.host,
                                     port=self.port,
                                     username=self.username, 
                                     password=self.password, 
                                     database=self.database)
    
    
    def __del__(self):
        print("Existing connection closed.")
        self.client.close()
    
    
    def get_measurements(self):
        """Get list of all measurments (series) in the DB.
        
        Arguments:
        --------------------------------------------------------------------------------
        None
        
        Returns:
        --------------------------------------------------------------------------------
        * measurments (list[str]): List of all measurement names in the db.
        
        Usage examples:
        --------------------------------------------------------------------------------
        q.get_measurements()
        >> ['series1', 'series2', 'series_with_no_tags']
        """
        query = f"SHOW MEASUREMENTS;"
        result = self.client.query(query).raw['series']
        if result:
            return [x[0] for x in result[0]['values']]
        else:
            return []
    
    
    def get_tags(self, series):
        """Get all tags (tag names) in the series.
        
        Tag names are returned as a list of strings. This list can be empty if query 
        returns no values, for example if there are no tags in the series or if there is
        no series with the given name.
        
        Arguments:
        --------------------------------------------------------------------------------
        * series (str): Name of the series.
        
        Returns:
        --------------------------------------------------------------------------------
        * tags (list[ster]): List of all tag names in the series.
        
        Usage examples:
        --------------------------------------------------------------------------------
        q.get_tags('series1')
        >> ['tag1', 'tag2']
        
        q.get_tags('nonexistent_series')
        >> []
        
        q.get_tags('series_with_no_tags')
        >> []
        """
        query = f'SHOW TAG KEYS FROM "{series}";'
        result = self.client.query(query).raw['series']
        if result:
            return [x[0] for x in result[0]['values']]
        else:
            return []
    
    
    def get_fields(self, series, return_types=False):
        """Get all fields in the series.
        
        If return_type=False (default) returns only field names as a list of strings.
        
        If return_types=True returns returns field names and corresponding field types 
        as a tuple of lists of strings.
        
        Field names are returned as a list of strings. This list can be empty if query 
        returns no values, for example if there is no series with the given name.
        
        Arguments:
        --------------------------------------------------------------------------------
        * series (str): Name of the series.
        * return_types (bool): Flag, indicates if field types should be returned.
        
        Returns:
        --------------------------------------------------------------------------------
        If return_types=False returns fields.
        
        If return_types=True returns tuple (fields, types).
        
        * fields (list[str]): List of field names in the series.
        * types (list[str]): List of corresponding InfluxDB types. types[i] is the type 
          of field[i]. InfluxDB types are 'integer', 'float', 'string' and 'boolean'.
        
        Usage examples:
        --------------------------------------------------------------------------------
        q.get_fields('series1')
        >> ['value']
        
        q.get_fields('series1', return_types=False)
        >> ['value']
        
        q.get_fields('series1', return_types=True)
        >> (['value'], ['integer'])
        
        q.get_fields('series2', return_types=True)
        >> (['num_petals', 'petal_length', 'species_name', 'is_female'], 
        ... ['integer', 'float', 'string', 'boolean'])
        
        q.get_fields('nonexistent_series')
        >> []
        """
        
        query = f'SHOW FIELD KEYS FROM "{series}";'
        result = self.client.query(query).raw['series']
        if result:
            if return_types:
                return ([x[0] for x in result[0]['values']], [x[1] for x in result[0]['values']])
            else:
                return [x[0] for x in result[0]['values']]
        else:
            if return_types:
                return ([], [])
            else:
                return []
    
    
    def get_keys(self, series, tag):
        """Get list of all tag values for a given tag name in the series.
        
        Tag values are returned as a list of strings. This list can be empty if query 
        returns no values, for example if there are no tags with the given name in the 
        series or if there is no series with the given name.
        
        Arguments:
        --------------------------------------------------------------------------------
        * series (str): Name of the series.
        * key (str): Name of the key.
        
        Returns:
        --------------------------------------------------------------------------------
        * keys (list[str]): List of all values of the tag in the series.
        
        Usage examples:
        --------------------------------------------------------------------------------
        q.get_keys('series1', 'tag1')
        >> ['foo', 'bar']
        
        q.get_keys('series1', 'nonexistent_tag')
        >> []
        
        q.get_keys('nonexistent_series', 'tag1')
        >> []
        """
        query = f'SHOW TAG VALUES FROM "{series}" WITH KEY = "{str(tag)}";'
        result = self.client.query(query).raw['series']
        if result:
            return [x[1] for x in result[0]['values']]
        else:
            return []
    
    
    def get_data(self, series, fields, keys=None, start=None, stop=None, local_tz=False):
        """Get data (records) for specified fields/tags in the series and return it as dict
        of columns.
        
        Optionally data can be constrained by field/tag values (only equality is tested)
        and/or time interval.
        
        Returns dictionary of numpy arrays with keys being 'time' for timestamps and 
        whatever field names are passed in the fields argument.
        
        Arguments:
        --------------------------------------------------------------------------------
        * series (str): Name of the series.
        * fields (obj): Name(s) of the fields in series. Depending on type is is 
          interpreted as following:
          + string: Interpreted as single field name to return. If fields='*' then all 
            fields and tags will be returned.
          + list/tuple/set: Interpreted as collection of field and tag names to return.
          + dict: Dict keys will be interpreted as field/tag names and corresponding
            values will be interpreted as numpy types (or names of numpy types) of 
            corresponding fields/tags. Output will be converted from InfluxDB types to 
            types specified in the dict. Use None as field type to to use type 
            autodetection and/or avoid type conversion for that field.
        * keys (None|dict): None or dictionary of key: value pairs. Dict keys specify 
          field/tag names and values specify corresponding values, each value can be 
          singular value or sequence (list/tuple/set) of values. Only records where 
          fields/tags have (one of) corresponding values will be selected. If None then
          no filtering by field/tag value will happen. All values are tested by
          equality, if several keys are specified then all key need to pass equality
          test (different keys are joined by AND), if key is associated with several 
          values then one of these values should pass the test (different vey values are
          joined by OR). See usage examples.
        * start (None|str|int|datetime): Inclusive lower time boundary for returned 
          data. Only records with time >= start will be returned. None indicates no 
          lower boundary, string is interpreted as timestring, int interpreted as Unix
          timestamp, datetime is used as-is.
        * stop (None|str|int|datetime): Exclusive upper time boundary for returned data. 
          Only records with time < stop will be returned. None indicates no upper 
          boundary, string is interpreted as timestring, int interpreted as Unix 
          timestamp, datetime is used as-is.
        * local_tz: Falg, indicates whether user uses local time ot UTC time in their 
          code. InfluxDb is assumed to always  hold timestamps in UTC. If True then 
          timezone correction will be applied to start and stop arguments and to all 
          returned timestamps.
        
        Returns:
        --------------------------------------------------------------------------------
        * data (dict[str: np.array]): Dictionary with keys being field names and values
          being numpy arrays of corresponding field/tag values. To get i'th row of 
          returned data use [col[i] for col in data.values()].
        
        Usage examples:
        --------------------------------------------------------------------------------
        # Use '*' to select all fields/tags
        q.get_data('series1', '*')
        >> {'time': array(['2019-11-05T00:00:00.000000000', 
        ...                '2019-11-05T06:00:00.000000000', 
        ...                '2019-11-06T00:00:00.000000000'], dtype='datetime64[ns]'),
        ... 'tag1': array(['foo', 'bar', 'foo'], dtype='<U3'),
        ... 'tag2': array(['1', '2', '3'], dtype='<U1'),
        ... 'value': array([1.0, 1.5, 2.0], dtype=float64)}
        
        # start is inclusive
        q.get_data('series1', 'value', start='2019-11-05 06:00')
        >> {'time': array(['2019-11-05T06:00:00.000000000', 
        ...                '2019-11-06T00:00:00.000000000'], dtype='datetime64[ns]'),
        ... 'value': array([1.5, 2.0], dtype=float64)}
        
        # stop is exclusive
        q.get_data('series1', ['value', 'tag1'], stop='2019-11-06')
        >> {'time': array(['2019-11-05T00:00:00.000000000', 
        ...                '2019-11-05T06:00:00.000000000'], dtype='datetime64[ns]'),
        ... 'value': array([1.0, 1.5], dtype=float64),
        ... 'tag1': array(['foo', 'bar'], dtype='<U3')}
        
        # Specify key value
        q.get_data('series1', '*', {'tag1': 'foo'})
        >> {'time': array(['2019-11-05T00:00:00.000000000', 
        ...                '2019-11-06T00:00:00.000000000'], dtype='datetime64[ns]'),
        ... 'tag1': array(['foo', 'foo'], dtype='<U3'),
        ... 'tag2': array(['1', '3'], dtype='<U1'),
        ... 'value': array([1.0, 2.0], dtype=float64)}
        
        # Specify multiple values for one key and use autoconversion to string
        q.get_data('series1', 'value', {'tag2': [1, 2]})
        >> {'time': array(['2019-11-05T00:00:00.000000000', 
        ...                '2019-11-05T06:00:00.000000000'], dtype='datetime64[ns]'),
        ... 'tag1': array(['foo', 'bar'], dtype='<U3'),
        ... 'tag2': array(['1', '2'], dtype='<U1'),
        ... 'value': array([1.0, 1.5], dtype=float64)}
        
        # Specify multiple keys
        q.get_data('series1', 'value', {'tag1': 'foo', 'tag2': [1, 2]})
        >> {'time': array(['2019-11-05T00:00:00.000000000'], dtype='datetime64[ns]'),
        ... 'tag1': array(['foo'], dtype='<U3'),
        ... 'tag2': array(['1'], dtype='<U1'),
        ... 'value': array([1.0], dtype=float64)}
        """
        def _tz_convert(t, local_tz=False):
            # Never adjust timezone for epoch timestamps
            if isinstance(t, int):
                return t
            tz = datetime.now().astimezone().tzinfo if local_tz else 'UTC'
            t = pd.Timestamp(t)
            if t.tz:
                # Always convert aware Timestamp to UTC timezone
                return f"'{t.tz_convert(None)}'"
            else:
                # Naive Timestamps can be treated as representing UTC or local time
                return f"'{t.tz_localize(tz).tz_convert(None)}'"
        
        def _type_cast(value, dtype):
            if dtype is None:
                return value
            if dtype.kind == 'M':
                return pd.Timestamp(value).tz_convert(None).asm8
            if dtype.kind == 'm':
                return pd.Timedelta(value).asm8
            else:
                return value
        
        def _destructure(key, val):
            if type(val) in (list, tuple, set):
                destruct = [f"\"{key!s}\" = '{v!s}'" for v in val]
                return f"({' OR '.join(destruct)})"
            else:
                return f"(\"{key!s}\" = '{val!s}')"
        
        time_type = np.dtype('<M8[ns]')
        default_type = np.dtype('O')
        type_conversion = {'integer': 'int64', 'float': 'float64', 'string': 'O', 'boolean': 'bool'}
        ftypes = {'time': time_type}
        dbtags = self.get_tags(series)
        string_fields = dbtags
        for f in dbtags:
            ftypes[f] = np.dtype('O')
        dbfields, dbtypes = self.get_fields(series, return_types=True)
        for f, t in zip(dbfields, dbtypes):
            if t == 'string':
                string_fields += [f]
            ftypes[f] = np.dtype(type_conversion[t])
        dballf = dbfields + dbtags
        if type(fields) is dict:
            _fields = []
            for f, t in fields.items():
                if f == '*':
                    _fields += dballf
                else:
                    if t is not None:
                        ftypes[f] = np.dtype(type_conversion.get(t, t))
                    _fields += [f'{f!s}']
            fields = _fields
        elif type(fields) in (list, tuple, set):
            _fields = []
            for f in fields:
                if f == '*':
                    _fields += dballf
                else:
                    _fields += [f'{f!s}']
            fields = _fields
        elif type(fields) is str:
            fields = dballf if fields == '*' else [f'{fields!s}']
        else:
            raise TypeError(f"fields should be a string, list, tuple, set or dict but {type(fields)} was passed")
        if 'time' not in fields:
            fields = ['time'] + fields
        for f in fields:
            if f not in ftypes:
                ftypes[f] = default_type
        if keys is None or keys == {}:
            where_clause = ""
        elif type(keys) is not dict:
            raise ValueError(f"keys should be None or dic of key: value pairs but {type(keys)} was passed")
        else:
            where_clause = f" WHERE {' AND '.join([_destructure(k, v) for k, v in keys.items()])}"
        time_query = ''
        if start is not None:
            time_query += f" AND time >= {_tz_convert(start, local_tz=local_tz)}"
        if stop is not None:
            time_query += f" AND time < {_tz_convert(stop, local_tz=local_tz)}"
        qfields = [f'"{f}"' for f in fields]
        query = f'SELECT {", ".join(qfields)} FROM "{series}"{where_clause}{time_query};'
        processed_query = self.client.query(query).raw['series']
        result = {}
        if processed_query:
            data = processed_query[0]['values']
            #fields = processed_query[0]['columns']
        else:
            data = []
        for field in fields:
            result[field] = np.zeros(len(data), dtype=ftypes[field])
        for i, row in zip(count(), data):
            for value, field in zip(row, fields):
                result[field][i] = _type_cast(value, ftypes[field])
        for f in fields:
            if f in string_fields:
                result[f] = result[f].astype('U')
        return result

    
class CycleAnalyzer():
    """Class to analyze circadian cycles given timestamp data.
    
    Initialization:
    --------------------------------------------------------------------------------
    
    CycleAnalyzer(timestamps, activity=None, night=None, step='1m', 
                  start=None, stop=None, descr='', 
                  max_gap='1m', min_duration='1m', min_activity=1, 
                  min_data_points=1)
    * timestamps (np.array[np.timedelta64]): Timestamps of activity records.
    * activity (None|np.array[int|float]): Number of activity events associated with 
      each timestamp or other activity measuremant. If None then it will be assumed 
      that activity=1 for each timestamp. Essentially it is weights used for each 
      timestamp during binning.
    * night (None|np.array[bool]): Boolean array denoting whether there was night 
      (night[i] == True) or day (night[i] == False) at i'th timestamp. If None then
      it will be assumed that night is True for each timestamp. During binning if 
      there are conflicting values for night in one bin (timestamps with both 
      night=True and night=False fall into the bin) then night=True will be written 
      for that bin (i.e. True values override False ones in the same bin).
    * step (str|int|timedelta): Discretization step. All data will be disretized by 
      binning it into bins of this size. String interpreted as timedelta string, int
      initerpreted as number of nanoseconds and timedelta used as-is.
    * start (None|str|int|datetime): Inclusive date for lower data time boundary.
      Only records with time.day() >= start will be processed. None indicates no 
      lower boundary, string is interpreted as timestring, int interpreted as Unix 
      timestamp, datetime is used as-is.
    * stop (None|str|int|datetime): Exclusive date for upper data times boundary.
      Only records with time.day() < stop will be processed. None indicates no upper
      boundary, string is interpreted as timestring, int interpreted as Unix 
      timestamp, datetime is used as-is.
    * descr (str): Textual description that will be added to the end of plot 
      headers. Use it to specify the source of data on the plots (for example to 
      specify what specimen(s) was used to generate timeseries).
    * max_gap (str|int|timedelta): Maximal gap between two consecutive activity
      events. Consecutive events with distance between them larger than max_gap will
      belong to different activity bouts. String interpreted as timedelta string, 
      int initerpreted as number of nanoseconds and timedelta used as-is.
    * min_duration (str|int|timedelta): Minimal duration of activity bout. Activity 
      bouts with shorter duration (defined as time difference between the last 
      activity event in a bout and the first one) will be discarded. String 
      interpreted as timedelta string, int initerpreted as number of nanoseconds and
      timedelta used as-is.
    * min_activity (int): Minimal value of (binned) activity. Bins with activity 
      less than min_activity will be discarded during activity bout calculations. 
      E.g. if self.step = '5 min' and min_activity = 6 then data will be binned 
      into 5 minute bins and during activity bout calculation bins with activity < 6
      will be treated asif no activity was occuring during their respective 
      intervals.
    * min_data_points: Minimum number of data points (records) in a day to keep it. 
      Days with less data points (records) will be filtered out.
    
    Attributes and properties:
    --------------------------------------------------------------------------------
    
    * start (np.datetime64): Adjusted lower time boundary (inclusive) of data 
      included in analysis. Due to start time adjustion it will be different from 
      00:00:00 but it is guaranteed that self.start will belong to the same day 
      (date) as the start argument passed during class initialization (or that it 
      will fall in the same day as first timestamp in timestamps argument if start 
      is None).
    * stop (np.datetime64): Adjusted upper time boundary (exclusive) of data 
      included in analysis. Due to start time adjustion it will be different from 
      00:00:00 but it is guaranteed that self.stop will be no less than stop 
      argument passed during class initialization and that self.stop - self.start 
      will be equal to the whole number of days.
    * step (np.timedelta64): Same as __init__ argument.
    * steps_per_day (int): Numbers of steps (bins) in a day.
    * descr (str): Same as __init__ argument.
    * total_days (int): Total number of days (including those that were filtered 
      out) between start and stop timestamps. E.g. data timespan in days.
    * days (int): Number of days that wasn't filtered out due to low activity. 
      days=self.daily_mask.sum() and days <= total_days.
    * daily_mask (np.array[bool]): Mask calculated from data and min_data_points.
      Numpy array of length equal to total_days. Holds True for days that weren't
      filtered out due to low activity and False for days that were.
    * min_data_points (int): Same as __init__ argument.
    * max_gap (np.timedelta64): Same as __init__ argument, but converted to 
      np.timedelta64[m] (minute precision).
    * min_duration (np.timedelta64): Same as __init__ argument, but converted to 
      np.timedelta64[m] (minute precision).
    * min_activity (int): Same as __init__ argument.
    * timestamps (np.array[np.datetime64]): Property that returns bin starts 
      (discrete time points). Days with number of data points less than 
      min_data_points are not included.
    * activity (np.array[int|float]): Property that return activity values for each 
      bin. Activity value for each bin is equal to sum of activity values for input 
      data point that fall into this bin. Days with number of data points less than 
      min_data_points are not included.
    * night (np.array[bool]): Property that returns filtered night values for each 
      bin. True values indicate that there was night (light was turned off) while 
      False values indicate that during that time interval light was turned on. Days
      with number of data points less than min_data_points are not included.
    * bouts (np.array[int]): Precalculated bouts to be used in class methods when 
      bouts=True is passed to them.
    
    
    Methods:
    --------------------------------------------------------------------------------
    Most methods can base their analysis on either number of activity events or 
    precalculated activity bouts. All such methods accept optional bouts argument.
    
    plot_* methods should be used to plot data. All such methods accept following 
    arguments:
    * filename (None|str|PathLike): If None plot will be displayed otherwise it will
      not be displayed but instead saved to file specified by string or PathLike 
      object.
    * width (int): Width of plot in pixels.
    * height (int): For all methods except plot_actogram() it is height of plot in 
      pixels. For plot_actogram() it is height of subplots for each day, total plot 
      height will be height * [number of days to plot] plus top and bottom margins.
    * dpi (int): Resolution for displaying plot.
    
    List of methods:
    * activity_bouts: Calculate activity bouts using provided parameters.
    * update_bouts:  Re-calculate and update self.bouts using provided parameters.
    * filter_inactive: Re-filter days based on new minimal daily number of data points.
    * plot_actogram: Plot double actogram with right half shifted by 1 day.
    * periodogram: Calculate periodogram for the range of periods.
    * plot_periodogram: Calculate and plot periodogram for the range of periods.
    * light_activity: Calculate light phase activity.
    * plot_light_activity: Calculate and plot light phase activity for each day.
    * interdaily_stability: Calculate interdaily stability.
    * intradaily_variability: Calculate intradaily variability.
    * plot_intradaily_variability: Calculate and plot intradaily variability for each day.
    * relative_amplitude: Calculate relative amplitude.
    * plot_relative_amplitude: Calculate and plot relative amplitude for each day.
    * daily_bouts: Calculate daily activity bout statistics.
    * plot_daily_bouts: Calculate and plot daily activity bout statistics.
    * plot_bout_hist: Plot histogram of activity bout duration distribution.
    * activity_onset: Calculate activity onset for each day.
    * plot_activity_onset: Calculate and plot activity onset for each day.
    """
    
    
    # Time constants used in class methods
    __t0 = np.datetime64(0, 'm')
    __zero = np.timedelta64(0, 'm')
    __minute = np.timedelta64(1, 'm')
    __hour = np.timedelta64(60, 'm')
    __day = np.timedelta64(60*24, 'm')
    
    
    def __init__(self, timestamps, activity=None, night=None, step='1m', start=None, stop=None, descr='',
                 max_gap='1m', min_duration='1m', min_activity=1, min_data_points=1):
        
        # Fill missing values and check for dimensions
        if activity is None:
            activity = np.ones(timestamps.size, dtype='int')
        elif timestamps.size != activity.size:
            raise ValueError(f"activity should have same size as timestamps")
        if night is None:
            night = np.ones(timestamps.size, dtype='bool')
        elif timestamps.size != night.size:
            raise ValueError(f"night should have same size as timestamps")
        
        # Check for valid step size
        self.step = pd.Timedelta(step).asm8
        if (self.step < self.__minute) or (self.step % self.__minute != self.__zero):
            raise ValueError(f"step must be a whole number of minutes")
        self.step = self.step.astype('<m8[m]')
        if self.__day % self.step != self.__zero:
            raise ValueError(f"day should be divisible by step size")
        self.steps_per_day = self.__day // self.step # Steps Per Day
        
        # Handle start and stop positions
        self.start = timestamps[0]
        self.start -= (self.start - self.__t0) % self.__day
        if start is not None:
            self.start = max(self.start, pd.Timestamp(start).asm8.astype('<M8[D]'))
        self.start = self.start.astype('<M8[m]')
        self.stop = timestamps[-1]
        # stop is exclusive
        self.stop += (self.start - self.stop - self.step) % self.__day + self.step
        if stop is not None:
            self.stop = min(self.stop, pd.Timestamp(stop).asm8.astype('<M8[D]'))
        self.stop = self.stop.astype('<M8[m]')
        self.total_days = (self.stop - self.start) // self.__day
        if self.total_days == 0:
            raise RuntimeError(f"No data points inside specified time range")
        
        # Discretize data so it will be alingned to regular (uniform) 1D grid.
        # We need this step because input will have values only at points where activity > 0,
        #   thus distance between 2 consecutive input data points will vary.
        intervals = np.arange(self.start, self.stop + self.step, self.step)
        self.__timestamps = intervals[:-1]
        self.__activity, _ = np.histogram(timestamps, intervals, weights=activity)
        
        # Here and later day and night refers to lights on/off conditions while calendar day refers to 24-hour 
        #   calendar day.
        # Because input data points distributed inhomogenously, apparent night and day beggining/end will
        #   vary from one calendar day to another even if day/night cycle is the same for each calendar day.
        # To work around this issue and assign same day/night boundaries across several calendar days we will
        #   assign negative values to points where night=False, positive values to points where night=True and
        #   value of zero to points for which we have no data.
        # Then we will align several calendar days to fill the gaps based on available data.
        # Finally we will fill the remaining gaps by trying to align day/night boundaries to some "pretty" values.
        # The algorithm also provide possibility for day/night boundaries that differ for different calendar days,
        #   but will try to make them as uniform as possible.
        #List of all 24-hour day/night patterns
        patterns = []
        # Number of calendar days that follow each day/night pattern, sum(pattern_days) = self.total_days
        pattern_days = [0]
        self.__night = np.zeros(self.steps_per_day * self.total_days, dtype='bool')
        night_array, _ = np.histogram(timestamps[night], intervals)
        night_array = night_array.astype('bool').reshape(self.total_days, self.steps_per_day)
        day_array, _ = np.histogram(timestamps[~night], intervals)
        day_array = day_array.astype('bool').reshape(self.total_days, self.steps_per_day)
        # If at some step there are both night and day data points, keep only one
        #night_array[day_array] = False # Option a)
        day_array[night_array] = False # Option b)
        # Current day and night patterns
        day_pattern = np.zeros(self.steps_per_day, dtype='bool')
        night_pattern = np.zeros(self.steps_per_day, dtype='bool')
        # Loop through each calendar day and assign day/night values to current day/night pattern based on  
        #   available data points for that calendar day.
        # Positive pattern values correspont to night while negative pattern values correspont to day.
        #   Zero values correspond to no available data and they will be filled during next stage.
        # In case of conflicting day/night values create new day/night pattern.
        for d in range(self.total_days):
            # Check that night and day phases for current day are not overlapping with phases in current pattern
            if np.any((day_pattern & night_array[d]) | (night_pattern & day_array[d])):
                # If night/day phases overlap with current pattern, finalize pattern and start new one.
                patterns.append(night_pattern.astype('int') - day_pattern.astype('int'))
                pattern_days.append(1)
                day_pattern = day_array[d].copy()
                night_pattern = night_array[d].copy()
            else:
                # If day/night phases don't overlap, update current day and night patterns and last pattern_days
                day_pattern |= day_array[d]
                night_pattern |= night_array[d]
                pattern_days[-1] += 1
        else:
            # Append last day/night pattern
            patterns.append(night_pattern.astype('int') - day_pattern.astype('int'))
        # Fill unassigned values in patterns and determine day/night boundaries
        # "Pretty" time values (in minutes) that will be favoured for day/night boundaries.
        pretty_numbers = [60, 30, 15, 10, 5]
        pretty_numbers = [n // self.step.astype('int') for n in pretty_numbers if n % self.step.astype('int') == 0]
        # Alignment to the one step is always valid
        if not pretty_numbers or pretty_numbers[-1] != 1:
            pretty_numbers.append(1)
        start_offset = ((self.start - self.__t0) % self.__day) // self.step
        pattern_start = 0
        boundaries = np.zeros(self.steps_per_day, dtype='int')
        nighttime = np.zeros(self.steps_per_day, dtype='int')
        for pattern, ndays in zip(patterns, pattern_days):
            start_idx = 0
            last_idx = 0
            last_val = 0
            for i in np.nonzero(pattern)[0]:
                if pattern[i] == -last_val:
                    # Try to align boundaries to "pretty" values
                    for n in pretty_numbers:
                        if i - (i + start_offset) % n > last_idx - 1:
                            last_idx = i - (i + start_offset) % n
                            break
                    pattern[start_idx : last_idx] = last_val
                    start_idx = last_idx
                    last_idx = i + 1
                    last_val = pattern[i]
                else:
                    last_val = pattern[i]
                    last_idx = i + 1
            else:
                pattern[start_idx : ] = last_val
            self.__night[pattern_start * self.steps_per_day : 
                         (pattern_start + ndays) * self.steps_per_day] = np.tile(pattern > 0, ndays)
            pattern_start += ndays
            # We are interested only in night -> day borders, that's why less-than-zero condition
            boundaries += (np.diff(pattern, prepend=pattern[-1]) < 0) * ndays
            nighttime += (pattern > 0)*ndays
        boundary_idx = np.nonzero(boundaries)[0]
        if boundary_idx.size > 0:
            # This sorting order prioritizes daytime over presense of night/day borders at the start of each day 
            boundary_idx = boundary_idx[np.lexsort((-boundaries[boundary_idx], nighttime[boundary_idx]))][0]
            # This sorting order prioritizes presense of night/day borders over daytime at the start of each day
            #boundary_idx = boundary_idx[np.lexsort((nighttime[boundary_idx], -boundaries[boundary_idx]))][0]
        else:
            boundary_idx = 0
        # Adjust start and stop
        self.start += boundary_idx * self.step
        self.stop += boundary_idx * self.step
        start_idx = boundary_idx
        stop_idx = start_idx + self.total_days * self.steps_per_day
        # Extend data by 1 day because the shift in start position
        if start_idx > 0:
            self.__timestamps = np.append(self.__timestamps, 
                                          np.arange(self.__day, step=self.step) 
                                          + self.__timestamps[-1] + self.step)[start_idx : stop_idx]
            self.__activity = np.append(self.__activity, 
                                        np.zeros(self.steps_per_day, dtype='int'))[start_idx : stop_idx]
            self.__night = np.append(self.__night, 
                                     self.__night[-self.steps_per_day : ])[start_idx : stop_idx]
        
        # Mask out datapoints for inactive days
        self.daily_mask = np.ones(self.total_days, dtype='bool')
        self.__mask = np.ones_like(self.__timestamps, dtype='bool')
        self.days = self.total_days
        self.min_data_points = min_data_points
        self.filter_inactive(min_data_points=min_data_points)
        
        # Calculate bouts
        self.update_bouts(max_gap, min_duration, min_activity)
        
        self.descr = descr
        
    
    @property
    def timestamps(self):
        return self.__timestamps[self.__mask]
    
    @property
    def activity(self):
        return self.__activity[self.__mask]
    
    @property
    def night(self):
        return self.__night[self.__mask]
    
    @property
    def bouts(self):
        return self.__bouts[self.__mask]
    
    
    def __get_step(self, step=None):
        if step is None:
            step = self.step
        else:
            step = pd.Timedelta(step).asm8.astype('<m8[m]')
        if self.__day % step:
            raise ValueError(f"there should be whole number of steps in 1 day")
        steps_per_day = self.__day // step
        if steps_per_day == 0:
            raise ValueError(f"step can't be larger that 1 day")
        return step, steps_per_day
    
    
    def __auc(self, values, dx, method='simps'):
        if values.size == 1:
            return values * dx
        else:
            l = dx*(values[0] - (values[1] - values[0])*dx/4)/2
            r = dx*(values[-1] - (values[-2] - values[-1])*dx/4)/2
        if method == 'midpoint':
            return values.sum() * dx
        elif method == 'trapz':
            return np.trapz(values, dx=dx) + l + r
        elif method == 'simps':
            return integrate.simps(values, dx=dx) + l + r
        else:
            raise ValueError(f"Unknown integration method: '{method}'")
    
    
    def __discretize(self, weights, step):
        step, steps_per_day = self.__get_step(step)
        result, intervals = np.histogram(self.timestamps,
                                         np.arange(self.start, self.stop + step, step, dtype='<M8[m]'),
                                         weights=weights)
        mask = np.repeat(self.daily_mask, steps_per_day)
        return (result[mask], intervals[:-1][mask])
    
    
    def __activity_bouts(self, max_gap=None, min_duration=None, min_activity=None):
        if max_gap is None:
            max_gap = self.max_gap
        else:
            max_gap = pd.Timedelta(max_gap).asm8.astype('<m8[m]')
            if max_gap % self.step != self.__zero:
                raise ValueError(f"max_gap should be multiple of discretization step ({str(self.step)})")
        if min_duration is None:
            min_duration = self.min_duration
        else:
            min_duration = pd.Timedelta(min_duration).asm8.astype('<m8[m]')
            if min_duration % self.step != self.__zero:
                raise ValueError(f"min_duration should be multiple of discretization step ({str(self.step)})")
        if min_activity is None:
            min_activity = self.min_activity
        max_gap = max_gap // self.step
        min_duration = min_duration // self.step
        bouts = np.zeros_like(self.__activity, dtype='bool')
        indexes = np.nonzero(self.__activity >= min_activity)[0]
        if len(indexes) > 0:
            bout_starts = indexes[(np.diff(indexes, prepend=indexes[0] - max_gap - 1) > max_gap).nonzero()[0]]
            bout_ends = indexes[(np.diff(indexes, append=indexes[0] + max_gap + 1) > max_gap).nonzero()[0]] + 1
        else:
            bout_starts = np.zeros(0)
            bout_ends = np.zeros(0)
        for s, e in zip(bout_starts, bout_ends):
            if e - s >= min_duration:
                bouts[s:e] = True
        return bouts.astype('int')
    
    
    def activity_bouts(self, max_gap=None, min_duration=None, min_activity=None):
        """Calculate activity bouts using provided parameters.
        
        Discretization step is taken from class initialization time (self.step). Does 
        not unpdate self.bouts, use update_bouts() for that.

        Arguments:
        --------------------------------------------------------------------------------
        * max_gap (None|str|int|timedelta): Maximal gap between two consecutive activity
          events. Consecutive events with distance between them larger than max_gap will
          belong to different activity bouts. None stands for self.max_gap, string 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * min_duration (None|str|int|timedelta): Minimal duration of activity bout. 
          Activity bouts with shorter duration (defined as time difference between the 
          last activity event in a bout and the first one) will be discarded. None 
          stands for self.min_duration, string interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * min_activity (None|int): Minimal value of (binned) activity. Bins with 
          activity less than min_activity will be discarded during activity bout 
          calculations. E.g. if self.step = '5 min' and min_activity = 6 then data will
          be binned into 5 minute bins and during activity bout calculation bins with 
          activity < 6 will be treated asif no activity was occuring during their 
          respective intervals. None stands for self.min_activity.
        
        Returns:
        --------------------------------------------------------------------------------
        * bouts (np.array[int]): Numpy integer array which holds 1 for steps that belong
          to some activity bout and 0 otherwise. Consecutive 1's in bouts belong to the 
          same bout.
        """
        return self.__activity_bouts(max_gap, min_duration, min_activity)[self.__mask]
    
    
    def update_bouts(self, max_gap=None, min_duration=None, min_activity=None):
        """Re-calculate and update self.bouts using provided parameters.
        
        All subsequent class method calls will use new bouts. Also updates max_gap, 
        min_duration and min_activity if they are not None.
        
        Discretization step is taken from class initialization time (self.step). Returns
        None.
        
        Arguments:
        --------------------------------------------------------------------------------
        * max_gap (None|str|int|timedelta): Maximal gap between two consecutive activity
          events. Consecutive events with distance between them larger than max_gap will
          belong to different activity bouts. None stands for self.max_gap, string 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * min_duration (None|str|int|timedelta): Minimal duration of activity bout. 
          Activity bouts with shorter duration (defined as time difference between the 
          last activity event in a bout and the first one) will be discarded. None 
          stands for self.min_duration, string interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * min_activity (None|int): Minimal value of (binned) activity. Bins with 
          activity less than min_activity will be discarded during activity bout 
          calculations. E.g. if self.step = '5 min' and min_activity = 6 then data will
          be binned into 5 minute bins and during activity bout calculation bins with 
          activity < 6 will be treated asif no activity was occuring during their 
          respective intervals. None stands for self.min_activity.
        
        Returns:
        --------------------------------------------------------------------------------
        None
        """
        if max_gap:
            max_gap = pd.Timedelta(max_gap).asm8.astype('<m8[m]')
            if max_gap < self.step:
                max_gap = self.step
            elif max_gap % self.step != self.__zero:
                raise ValueError(f"max_gap should be multiple of discretization step ({str(self.step)})")
            self.max_gap = max_gap
        else:
            max_gap = self.max_gap
        if min_duration:
            min_duration = pd.Timedelta(min_duration).asm8.astype('<m8[m]')
            if min_duration < self.step:
                min_duration = self.step
            elif min_duration % self.step != self.__zero:
                raise ValueError(f"min_duration should be multiple of discretization step ({str(self.step)})")
            self.min_duration = min_duration
        else:
            min_duration = self.min_duration
        if min_activity:
            if min_activity <= 0:
                raise ValueError(f"min_activity should be positive")
            self.min_activity = min_activity
        else:
            min_activity = self.min_activity
        self.__bouts = self.__activity_bouts(max_gap, min_duration, min_activity)
    
    
    def filter_inactive(self, min_data_points=1):
        """Re-filter days based on new minimal daily number of data points.
        
        All subsequent class method calls will use new filtered days.
        
        Arguments:
        --------------------------------------------------------------------------------
        * min_data_points: Minimum number of data points (records) in a day to keep it. 
          Days with less data points (records) will be filtered out.
        
        Returns:
        --------------------------------------------------------------------------------
        None
        """
        self.daily_mask[:] = False
        self.__mask[:] = False
        events, _ = np.histogram(self.__timestamps[self.__activity > 0], 
                                 np.arange(self.start, self.stop + self.__day, self.__day))
        self.daily_mask = (events >= min_data_points)
        self.days = self.daily_mask.sum()
        self.__mask = np.repeat(self.daily_mask, self.steps_per_day)
    
    
    def plot_actogram(self, step=None, bouts=False, log=False, activity_onset='step', percentile=20, N='6h', M='6h',
                      filename=None, width=1000, height=100, dpi=100):
        """Plot double actogram with right half shifted by 1 day.
        
        Night intervals for each day are also plotted on actogram as well as activity 
        onset for each day.
        
        
        Arguments:
        --------------------------------------------------------------------------------
        * step (None|str|int|timedelta): Bin size (number of bars on actogram will be 
          equal to [24 hours] / step). None stands for self.max_gap, string interpreted 
          as timedelta string, int initerpreted as number of nanoseconds and timedelta 
          used as-is.
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        * log (bool): Flag, indicates whether log of activity will be plotted. Has no 
          effect if bouts=True.
        * activity_onset (None|False|str): Shape of convolution kernel to use for 
          activity onset calculation. To turn activity onset display off pass None, 
          False or string 'none' (case-insensitive). Otherwise it should be one of the
          strings that self.activity_onset() method recognizes.
        * percentile (int): Percentile of daily non-zero activity to use as threshold 
          for activity onset calculation.
        * N (str|int|timedelta): Length of period of negative values (daytime, left 
          part) in convolution kernel for activity onset calculation. String interpreted
          as timedelta string, int initerpreted as number of nanoseconds and timedelta 
          used as-is.
        * M (str|int|timedelta): Length of period of positive values (nighttime, right 
          part) in convolution kernel for activity onset calculation. String interpreted
          as timedelta string, int initerpreted as number of nanoseconds and timedelta 
          used as-is.
        * filename (None|str|PathLike): If None plot will be displayed otherwise it will
          not be displayed but instead saved to file specified by string or PathLike 
          object.
        * width (int): Width of plot in pixels.
        * height (int): For all methods except plot_actogram() it is height of plot in 
          pixels. For plot_actogram() it is height of subplots for each day, total plot 
          height will be height * [number of days to plot] plus top and bottom margins.
        * dpi (int): Resolution for displaying plot.
        
        Returns:
        --------------------------------------------------------------------------------
        None
        """
        if filename is not None:
            filename = Path(filename)
        step, steps_per_day = self.__get_step(step)
        if str(activity_onset).lower() == 'none':
            activity_onset = False
        log = ~bouts & log
        bar_color = '#000000'
        night_color = '#808080'
        #bar_color = '#40444B'
        #night_color = '#CACFE2'
        onset_color = '#cc0000'
        if bouts:
            if step != self.step:
                values, timestamps = self.__discretize(self.bouts, step)
            else:
                values = self.bouts
                timestamps = self.timestamps
        else:
            if step != self.step:
                values, timestamps = self.__discretize(self.activity, step)
            else:
                values = self.activity
                timestamps = self.timestamps
        if log:
            values[values>1] = 1 + np.log(values[values>1])
        values = values.reshape(self.days, steps_per_day)
        night, _ = self.__discretize(self.night.astype('int'), step)
        night = (night>0).astype('int').reshape(self.days, steps_per_day)
        max_y = values.max()
        plots_height = height*self.days
        total_height = plots_height + 150
        fig, subplots = plt.subplots(self.days, 2, squeeze=False, sharex=True, sharey=True,
                                     figsize=(width/dpi, total_height/dpi), dpi=dpi,
                                     gridspec_kw={'hspace': 0, 
                                                  'wspace': 0, 
                                                  'top':1 - 100/total_height, 
                                                  'bottom': 50/total_height})
        plt.ylim(0, max_y)
        minute_offset = (self.start - self.__t0) % self.__hour
        if not minute_offset:
            first_tick = self.start
            tick_start = 0.0
        else:
            first_tick = self.start - minute_offset + self.__hour
            tick_start = (self.__hour - minute_offset) / self.__day
        hours_per_tick = 2
        tick_pos = np.arange(tick_start, 1 + tick_start, hours_per_tick/24) * steps_per_day
        tick_labels = []
        for i in range(len(tick_pos)):
            tick_label = pd.Timestamp(first_tick + i*hours_per_tick*self.__hour).strftime('%H')
            tick_labels.append(tick_label)
        fig.text(0.5, 1 - 50/total_height, f"Actogram {self.descr}", ha='center', fontsize=20, wrap=False)
        if activity_onset:
            onset = self.activity_onset(step, percentile, N, M, bouts, activity_onset)
            onset = ((onset - timestamps[0]) % self.__day) / self.__day * steps_per_day
        last_d = -1
        interval = np.arange(steps_per_day)
        for i in range(1, 2*self.days):
            d = i // 2
            if d != last_d:
                night_pos = timestamps[np.nonzero(np.diff(night[d], 
                                                          prepend=False, append=False))[0]].reshape(-1, 2)
                night_pos = ((night_pos - timestamps[0]) / self.__day) * steps_per_day
            last_d = d
            ax = subplots[d - (i+1)%2, (i+1) % 2]
            ax.bar(interval, values[d], width=1, align='edge', color=bar_color)
            for j in range(len(night_pos)):
                ax.axvspan(night_pos[j, 0], night_pos[j, 1], color=night_color, alpha=0.5)
            if not i%2:
                ax.yaxis.set_label_position('right')
            if activity_onset:
                ax.axvspan(onset[d], onset[d], color=onset_color)
            ax.set_yticks([])
            ax.set_ylabel(f"{pd.Timestamp(timestamps[d*steps_per_day]).strftime('%Y-%m-%d')}", 
                          rotation=0, fontsize=8, labelpad=40, va='center')
        plt.xticks(ticks=tick_pos, labels=tick_labels)
        plt.xlim([0, steps_per_day])
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    
    def periodogram(self, step=None, min_period='16h', max_period='32h', bouts=False):
        """Calculate periodogram for the range of periods.
        
        Returns tuple of numpy arrays first of which is time periods of length in range 
        from min_period to max_period (inclusive) and second is periodogram powers for 
        each period.
        
        If periods, powers = periodogram() then periods[powers.argmax()] will return 
        period with maximal periodogram power.

        Arguments:
        --------------------------------------------------------------------------------
        * step (None|str|int|timedelta): Step size for generating periods. First period 
          will have length min_period, second one will heve length min_period + step and
          so on. None stands for self.max_gap, string interpreted as timedelta string, 
          int initerpreted as number of nanoseconds and timedelta used as-is.
        * min_period (str|int|timedelta): Minimal period length, inclusive. String 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * max_period (str|int|timedelta): Maximal period length, inclusive. String 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        
        Returns:
        --------------------------------------------------------------------------------
        Tuple (periods, powers):
        * periods (np.array[np.timedelta64]): Periods in the range from min_period to
          max_period (inclusive).
        * powers (np.array[float]): Corresponding periodogram powers for each period.
        """
        step, _ = self.__get_step(step)
        min_period = pd.Timedelta(min_period).asm8.astype('<m8[m]')
        max_period = pd.Timedelta(max_period).asm8.astype('<m8[m]')
        if min_period % step + max_period % step != self.__zero:
                raise ValueError(f"min_period and max_period should be divisible "
                                 f"by step ({pd.Timedelta(step)})")
        if bouts:
            values, _ = self.__discretize(self.bouts, step)
        else:
            values, _ = self.__discretize(self.activity, step)
        # Pad zeros to not lose values at the end of data
        values = np.pad(values, (0, max_period//step - 1))
        n = values.size
        result = np.zeros(max_period//step - min_period//step + 1)
        for i, p in enumerate(np.arange(min_period//step, max_period//step + 1)):
            k = n//p
            tmp = values[:k*p].reshape((k, p))
            result[i] = k*p*tmp.mean(axis=0).var() / tmp.var()
        periods = np.arange(min_period, max_period + step, step, dtype='<m8[m]')
        return periods, result
    
    
    def plot_periodogram(self, step=None, min_period='16h', max_period='32h', bouts=False,
                         filename=None, width=1000, height=600, dpi=100):
        """Calculate and plot periodogram for the range of periods.
        
        Plot also includes indication of period with maximal periodogram power.
        
        Arguments:
        --------------------------------------------------------------------------------
        * step (None|str|int|timedelta): Step size for generating periods. First period 
          will have length min_period, second one will heve length min_period + step and
          so on. None stands for self.max_gap, string interpreted as timedelta string, 
          int initerpreted as number of nanoseconds and timedelta used as-is.
        * min_period (str|int|timedelta): Minimal period length, inclusive. String 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * max_period (str|int|timedelta): Maximal period length, inclusive. String 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        * filename (None|str|PathLike): If None plot will be displayed otherwise it will
          not be displayed but instead saved to file specified by string or PathLike 
          object.
        * width (int): Width of plot in pixels.
        * height (int): For all methods except plot_actogram() it is height of plot in 
          pixels. For plot_actogram() it is height of subplots for each day, total plot 
          height will be height * [number of days to plot] plus top and bottom margins.
        * dpi (int): Resolution for displaying plot.
        
        Returns:
        --------------------------------------------------------------------------------
        None
        """
        periods, values = self.periodogram(step, min_period, max_period, bouts)
        periods = periods.astype('int')
        hour = self.__hour.astype('int')
        graph_color = '#000000'
        if filename is not None:
            filename = Path(filename)
        fig = plt.figure(figsize=(width/dpi, height/dpi))
        n = periods.size
        offset = periods[0] % hour
        if not offset:
            start = periods[0]
        else:
            start = periods[0] - offset + hour
        tick_pos = np.arange(start, periods[-1] + hour - offset, hour)
        tick_labels = []
        for tick in tick_pos:
            tick_labels.append(str(tick//hour))
        plt.xticks(ticks=tick_pos.astype('int'), labels=tick_labels)
        plt.xlim([periods[0], periods[-1]])

        plt.plot(periods, values, color=graph_color)
        fig.text(0.5, 0.95, f"Periodogram {self.descr}", ha='center', fontsize=20, wrap=False)
        fig.text(0.5, 0.0, f"Maximal power at period "
                           f"{periods[values.argmax()] / hour :.2f} hours",
                 ha='center', fontsize=20, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    
    def light_activity(self, bouts=False, auc=False):
        """Calculate light phase activity.
        
        Returns tuple (daily_values, total) where daily_values holds light phase 
        activity calculated for each day and total holds light phase activity calculated
        from data for all days.
        
        Arguments:
        --------------------------------------------------------------------------------
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        * auc (bool): Flag, indicates whether to return AUC.
        
        Returns:
        --------------------------------------------------------------------------------
        Tuple (daily_values, total) if auc=False or tuple (daily_values, total, auc_val)
        if auc=True:
        * daily_values (np.array[float]): Light phase activity for each day.
        * total (float): Light phase activity calculated from data for all days.
        * auc_val (float): Area under the curve (integral).
        """
        result = np.zeros(self.total_days)
        if bouts:
            day_activity, _ = self.__discretize(self.bouts.astype('int') * ~self.night, self.__day)
            all_activity, _ = self.__discretize(self.bouts.astype('int'), self.__day)
        else:
            day_activity, _ = self.__discretize(self.activity * ~self.night, self.__day)
            all_activity, _ = self.__discretize(self.activity, self.__day)
        result = day_activity / all_activity
        mean_result = day_activity.sum() / all_activity.sum()
        if auc:
            return result, mean_result, self.__auc(result, 1)
        else:
            return result, mean_result
        
    
    
    def plot_light_activity(self, bouts=False, filename=None, width=1000, height=600, dpi=100):
        """Calculate and plot light phase activity for each day.
        
        Plot also includes total value based on data for all days.
        
        Arguments:
        --------------------------------------------------------------------------------
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        * filename (None|str|PathLike): If None plot will be displayed otherwise it will
          not be displayed but instead saved to file specified by string or PathLike 
          object.
        * width (int): Width of plot in pixels.
        * height (int): For all methods except plot_actogram() it is height of plot in 
          pixels. For plot_actogram() it is height of subplots for each day, total plot 
          height will be height * [number of days to plot] plus top and bottom margins.
        * dpi (int): Resolution for displaying plot.
        
        Returns:
        --------------------------------------------------------------------------------
        None
        """
        values, total, auc = self.light_activity(bouts, True)
        graph_color = '#000000'
        total_color = '#808080'
        max_ticks = 20
        if filename is not None:
            filename = Path(filename)
        fig = plt.figure(figsize=(width/dpi, height/dpi))
        #plt.ylim(0, 1)
        tick_step = self.days // (max_ticks - 1) + 1
        tick_mask = np.full(self.days, False, dtype='bool')
        for i in range(0, self.days, tick_step):
            tick_mask[i] = True
        tick_mask[-1] = True
        tick_pos = np.arange(self.days)[tick_mask]
        tick_labels = np.arange(self.start, self.stop, self.__day)[self.daily_mask][tick_mask].astype('datetime64[D]')
        plt.xticks(tick_pos, tick_labels, rotation=90)
        plt.plot(values, color=graph_color)
        plt.axhline(total, color=total_color)
        fig.text(0.5, 0.95, f"Light Phase Activity {self.descr}", ha='center', fontsize=20, wrap=False)
        fig.text(0.5, 0.9, f"AUC: {auc:.3f}", ha='center', fontsize=16, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    
    def interdaily_stability(self, step='1h', bouts=False):
        """Calculate interdaily stability.
        
        Small step values lead to very low interdaily stability even with stable 
        activity patterns.
        
        Arguments:
        --------------------------------------------------------------------------------
        * step (None|str|int|timedelta): Data discretization step used for calculations.
          None stands for self.max_gap, string interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        
        Returns:
        --------------------------------------------------------------------------------
        * interdaily_stability (float): Float in range [0, 1] (inclusive).
        """
        step, steps_per_day = self.__get_step(step)
        if bouts:
            values, _ = self.__discretize(self.bouts, step)
        else:
            values, _ = self.__discretize(self.activity, step)
        values = values.reshape(self.days, steps_per_day)
        result = 0.0
        var = values.var()
        if var and not np.isnan(var):
            result = values.mean(axis=0).var() / var
        return result
    
    
    def intradaily_variability(self, step='1h', bouts=False, auc=False):
        """Calculate intradaily variability.
        
        Returns tuple (daily_values, total) where daily_values holds intradaily 
        variability calculated for each day and total holds intradaily variability 
        calculated from data for all days.
        
        Small step values lead to very high interdaily variability even with stable 
        activity patterns.
        
        Arguments:
        --------------------------------------------------------------------------------
        * step (None|str|int|timedelta): Data discretization step used for calculations.
          None stands for self.max_gap, string interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        
        Returns:
        --------------------------------------------------------------------------------
        Tuple (daily_values, total) if auc=False or tuple (daily_values, total, auc_val)
        if auc=True:
        * daily_values (np.array[float]): Intradaily variability for each day.
        * total (float): Intradaily variability calculated from data for all days.
        * auc_val (float): Area under the curve (integral).
        """
        step, steps_per_day = self.__get_step(step)
        if bouts:
            values, _ = self.__discretize(self.bouts, step)
        else:
            values, _ = self.__discretize(self.activity, step)
        values = values.reshape(self.days, steps_per_day)
        result = np.zeros(self.days)
        tmp = (np.diff(values, axis=-1) ** 2).mean(axis=-1)
        var = values.reshape(self.days, steps_per_day).var(axis=-1)
        mask = (var > 0) & ~np.isnan(var)
        result[mask] = tmp[mask] / var[mask]
        total = 0.0
        var = values.var()
        if var and not np.isnan(var):
            total = (np.diff(values) ** 2).mean() / var
        if auc:
            return result, total, self.__auc(result, 1)
        else:
            return result, total
    
    
    def plot_intradaily_variability(self, step='1h', bouts=False,
                                    filename=None, width=1000, height=600, dpi=100):
        """Calculate and plot intradaily variability for each day.
        
        Plot also includes total value based on data for all days.
        
        Small step values lead to very high interdaily variability even with stable 
        activity patterns.
        
        Arguments:
        --------------------------------------------------------------------------------
        * step (None|str|int|timedelta): Data discretization step used for calculations.
          None stands for self.max_gap, string interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        * filename (None|str|PathLike): If None plot will be displayed otherwise it will
          not be displayed but instead saved to file specified by string or PathLike 
          object.
        * width (int): Width of plot in pixels.
        * height (int): For all methods except plot_actogram() it is height of plot in 
          pixels. For plot_actogram() it is height of subplots for each day, total plot 
          height will be height * [number of days to plot] plus top and bottom margins.
        * dpi (int): Resolution for displaying plot.
        
        Returns:
        --------------------------------------------------------------------------------
        None
        """
        values, total, auc = self.intradaily_variability(step, bouts, True)
        graph_color = '#000000'
        total_color = '#808080'
        max_ticks = 20
        if filename is not None:
            filename = Path(filename)
        fig = plt.figure(figsize=(width/dpi, height/dpi))
        tick_step = self.days // (max_ticks - 1) + 1
        tick_mask = np.full(self.days, False, dtype='bool')
        for i in range(0, self.days, tick_step):
            tick_mask[i] = True
        tick_mask[-1] = True
        tick_pos = np.arange(self.days)[tick_mask]
        tick_labels = np.arange(self.start, self.stop, self.__day)[self.daily_mask][tick_mask].astype('datetime64[D]')
        plt.xticks(tick_pos, tick_labels, rotation=90)
        #plt.ylim(0, max(total, values.max())*1.05)
        plt.plot(values, color=graph_color)
        plt.axhline(total, color=total_color)
        fig.text(0.5, 0.95, f"Intradaily Variability {self.descr}", ha='center', fontsize=20, wrap=False)
        fig.text(0.5, 0.9, f"AUC: {auc:.3f}", ha='center', fontsize=16, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    
    def relative_amplitude(self, most_active='10h', least_active='5h', bouts=False, auc=False):
        """Calculate relative amplitude.
        
        Returns tuple (daily_values, total) where daily_values holds relative amplitude 
        calculated for each day and total holds relative amplitude calculated from data 
        for all days.
        
        Arguments:
        --------------------------------------------------------------------------------
        * most_active (str|int|timedelta): Length of most active period. String 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * least_active (str|int|timedelta): Length of least active period. String 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        
        Returns:
        --------------------------------------------------------------------------------
        Tuple (daily_values, total) if auc=False or tuple (daily_values, total, auc_val)
        if auc=True:
        * daily_values (np.array[float]): Relative amplitude for each day.
        * total (float): Relative amplitude calculated from data for all days.
        * auc_val (float): Area under the curve (integral).
        """

        def window1d(a, width, step=1):
            return a[np.arange(0, width, step)[None, :] + np.arange(0, a.size-width+1, step)[:, None]]

        most_active = pd.Timedelta(most_active).asm8
        least_active = pd.Timedelta(least_active).asm8
        if most_active + least_active + min(most_active, least_active) > self.__day:
            raise ValueError(f"most_active + least_active + min(most_active, least_active) "
                             "should be no greater than 1 day")
        if most_active <= self.__zero:
            raise ValueError(f"most_active should be > 0")
        if least_active <= self.__zero:
            raise ValueError(f"least_active should be > 0")
        if most_active % self.step != self.__zero:
            raise ValueError(f"most_active should be divisible by instance step ({str(self.step)})")
        if least_active % self.step != self.__zero:
            raise ValueError(f"least_active should be divisible by instance step ({str(self.step)})")
        if bouts:
            values = self.bouts
        else:
            values = self.activity
        most_active_steps = most_active // self.step
        least_active_steps = least_active // self.step
        result = np.zeros(self.days)
        total_most_active = 0
        total_least_active = 0
        for i in range(self.days):
            start = i * self.steps_per_day
            stop = (i+1) * self.steps_per_day
            most_active_w = window1d(values[start : stop], most_active_steps).mean(-1)
            most_active_idx = most_active_w.argmax()
            most_active_val = most_active_w[most_active_idx]
            least_active_val_1 = np.inf
            least_active_val_2 = np.inf
            if most_active_idx >= least_active_steps:
                least_active_w = window1d(values[start : start + most_active_idx], 
                                          least_active_steps).mean(-1)
                least_active_idx = least_active_w.argmin()
                least_active_val_1 = least_active_w[least_active_idx]
            if most_active_idx + most_active_steps + least_active_steps <= self.steps_per_day:
                least_active_w = window1d(values[start + most_active_idx + most_active_steps : stop], 
                                          least_active_steps).mean(-1)
                least_active_idx = least_active_w.argmin()
                least_active_val_2 = least_active_w[least_active_idx]
            least_active_val = min(least_active_val_1, least_active_val_2)
            if least_active_val == np.inf:
                least_active_w = window1d(values[start : stop], least_active_steps).mean(-1)
                least_active_idx = least_active_w.argmin()
                least_active_val = least_active_w[least_active_idx]
                most_active_val_1 = -np.inf
                most_active_val_2 = -np.inf
                if least_active_idx >= most_active_steps:
                    most_active_w = window1d(values[start : start + least_active_idx], 
                                             most_active_steps).mean(-1)
                    most_active_idx = most_active_w.argmax()
                    most_active_val_1 = most_active_w[most_active_idx]
                if least_active_idx + least_active_steps + most_active_steps <= self.steps_per_day:
                    most_active_w = window1d(values[start + least_active_idx + least_active_steps : stop], 
                                             most_active_steps).mean(-1)
                    most_active_idx = most_active_w.argmax()
                    most_active_val_2 = most_active_w[most_active_idx]
                most_active_val = max(most_active_val_1, most_active_val_2)
            total_most_active += most_active_val
            total_least_active += least_active_val
            if most_active_val:
                result[i] = (most_active_val - least_active_val) / (most_active_val + least_active_val)
        total = 0.0
        if total_most_active:
            total = (total_most_active - total_least_active) / (total_most_active + total_least_active)
        if auc:
            return result, total, self.__auc(result, 1)
        else:
            return result, total
    
    
    def plot_relative_amplitude(self, most_active='10h', least_active='5h', bouts=False,
                                filename=None, width=1000, height=600, dpi=100):
        """Calculate and plot relative amplitude for each day.
        
        Plot also includes total value based on data for all days.
        
        Arguments:
        --------------------------------------------------------------------------------
        * most_active (str|int|timedelta): Length of most active period. String 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * least_active (str|int|timedelta): Length of least active period. String 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        * filename (None|str|PathLike): If None plot will be displayed otherwise it will
          not be displayed but instead saved to file specified by string or PathLike 
          object.
        * width (int): Width of plot in pixels.
        * height (int): For all methods except plot_actogram() it is height of plot in 
          pixels. For plot_actogram() it is height of subplots for each day, total plot 
          height will be height * [number of days to plot] plus top and bottom margins.
        * dpi (int): Resolution for displaying plot.
        
        Returns:
        --------------------------------------------------------------------------------
        None
        """
        values, total, auc = self.relative_amplitude(most_active, least_active, bouts, True)
        graph_color = '#000000'
        total_color = '#808080'
        max_ticks = 20
        if filename is not None:
            filename = Path(filename)
        fig = plt.figure(figsize=(width/dpi, height/dpi))
        tick_step = self.days // (max_ticks - 1) + 1
        tick_mask = np.full(self.days, False, dtype='bool')
        for i in range(0, self.days, tick_step):
            tick_mask[i] = True
        tick_mask[-1] = True
        tick_pos = np.arange(self.days)[tick_mask]
        tick_labels = np.arange(self.start, self.stop, self.__day)[self.daily_mask][tick_mask].astype('datetime64[D]')
        plt.xticks(tick_pos, tick_labels, rotation=90)
        #plt.ylim(0, 1)
        plt.plot(np.arange(self.days), values, color=graph_color)
        plt.axhline(total, color=total_color)
        fig.text(0.5, 0.95, f"Relative Amplitude {self.descr}", ha='center', fontsize=20, wrap=False)
        fig.text(0.5, 0.9, f"AUC: {auc:.3f}", ha='center', fontsize=16, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    
    def daily_bouts(self, max_gap=None, min_duration=None, min_activity=None):
        """Calculate daily activity bout statistics.
        
        First it calculates activity bouts based on provided parameters and then for 
        each day calculates number of activity bouts and average activity bout duration.
        
        Returns daily bout counts and daily bout average durations.
        
        Arguments:
        --------------------------------------------------------------------------------
        * max_gap (None|str|int|timedelta): Maximal gap between two consecutive activity
          events. Consecutive events with distance between them larger than max_gap will
          belong to different activity bouts. None stands for self.max_gap, string 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * min_duration (None|str|int|timedelta): Minimal duration of activity bout. 
          Activity bouts with shorter duration (defined as time difference between the 
          last activity event in a bout and the first one) will be discarded. None 
          stands for self.min_duration, string interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * min_activity (None|int): Minimal value of (binned) activity. Bins with 
          activity less than min_activity will be discarded during activity bout 
          calculations. E.g. if self.step = '5 min' and min_activity = 6 then data will
          be binned into 5 minute bins and during activity bout calculation bins with 
          activity < 6 will be treated asif no activity was occuring during their 
          respective intervals. None stands for self.min_activity.
        
        Returns:
        --------------------------------------------------------------------------------
        Tuple (bout_counts, bout_durations):
        * bout_counts (np.array[int]): Number of activity bouts in each day.
        * bout_durations (np.array[float]): Average activity bout durations for each day 
          in minutes.
        """
        bouts = self.activity_bouts(max_gap, min_duration, min_activity).reshape(self.days, 
                                                                              self.steps_per_day).astype('int')
        bout_counts = (np.diff(bouts, prepend=0, append=0, axis=-1) > 0).sum(axis=-1)
        bout_durations = np.zeros(self.days, dtype='float')
        mask = (bout_counts > 0)
        bout_durations[mask] = self.step.astype('int') * bouts.sum(axis=-1)[mask] / bout_counts[mask]
        return bout_counts, bout_durations
    
    
    def plot_daily_bouts(self, max_gap=None, min_duration=None, min_activity=None,
                         filename=None, width=1000, height=600, dpi=100):
        """Calculate and plot daily activity bout statistics.
        
        Bout counts are plotted as bar plot vs left y-axis and average bout durations 
        are plotted as line plot vs right y-axis.
        
        
        Arguments:
        --------------------------------------------------------------------------------
        * max_gap (None|str|int|timedelta): Maximal gap between two consecutive activity
          events. Consecutive events with distance between them larger than max_gap will
          belong to different activity bouts. None stands for self.max_gap, string 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * min_duration (None|str|int|timedelta): Minimal duration of activity bout. 
          Activity bouts with shorter duration (defined as time difference between the 
          last activity event in a bout and the first one) will be discarded. None 
          stands for self.min_duration, string interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * min_activity (None|int): Minimal value of (binned) activity. Bins with 
          activity less than min_activity will be discarded during activity bout 
          calculations. E.g. if self.step = '5 min' and min_activity = 6 then data will
          be binned into 5 minute bins and during activity bout calculation bins with 
          activity < 6 will be treated asif no activity was occuring during their 
          respective intervals. None stands for self.min_activity.
        * filename (None|str|PathLike): If None plot will be displayed otherwise it will
          not be displayed but instead saved to file specified by string or PathLike 
          object.
        * width (int): Width of plot in pixels.
        * height (int): For all methods except plot_actogram() it is height of plot in 
          pixels. For plot_actogram() it is height of subplots for each day, total plot 
          height will be height * [number of days to plot] plus top and bottom margins.
        * dpi (int): Resolution for displaying plot.
        
        Returns:
        --------------------------------------------------------------------------------
        None
        """
        bout_counts, bout_durations = self.daily_bouts(max_gap, min_duration, min_activity)
        graph_color = '#000000'
        bar_color = '#808080'
        max_ticks = 20
        if filename is not None:
            filename = Path(filename)
        fig = plt.figure(figsize=(width/dpi, height/dpi))
        tick_step = self.days // (max_ticks - 1) + 1
        tick_mask = np.full(self.days, False, dtype='bool')
        for i in range(0, self.days, tick_step):
            tick_mask[i] = True
        tick_mask[-1] = True
        tick_pos = np.arange(self.days)[tick_mask]
        tick_labels = np.arange(self.start, self.stop, self.__day)[self.daily_mask][tick_mask].astype('datetime64[D]')
        plt.xticks(tick_pos, tick_labels, rotation=90)
        plt.ylabel('N. bouts', fontsize=12)
        plt.bar(np.arange(self.days), bout_counts, color=bar_color)
        plt.twinx()
        plt.ylabel('Mean bout duration', fontsize=12)
        plt.plot(bout_durations, color=graph_color)
        fig.text(0.5, 0.95, f"Daily Bouts {self.descr}", ha='center', fontsize=20, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    
    def plot_bout_histogram(self, max_gap=None, min_duration=None, min_activity=None, bins=50,
                            filename=None, width=1000, height=600, dpi=100):
        """Plot histogram of activity bout duration distribution.
        
        Arguments:
        --------------------------------------------------------------------------------
        * max_gap (None|str|int|timedelta): Maximal gap between two consecutive activity
          events. Consecutive events with distance between them larger than max_gap will
          belong to different activity bouts. None stands for self.max_gap, string 
          interpreted as timedelta string, int initerpreted as number of nanoseconds and
          timedelta used as-is.
        * min_duration (None|str|int|timedelta): Minimal duration of activity bout. 
          Activity bouts with shorter duration (defined as time difference between the 
          last activity event in a bout and the first one) will be discarded. None 
          stands for self.min_duration, string interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * min_activity (None|int): Minimal value of (binned) activity. Bins with 
          activity less than min_activity will be discarded during activity bout 
          calculations. E.g. if self.step = '5 min' and min_activity = 6 then data will
          be binned into 5 minute bins and during activity bout calculation bins with 
          activity < 6 will be treated asif no activity was occuring during their 
          respective intervals. None stands for self.min_activity.
        * bins (int|np.array[int]): Number of bins or numpy array of bin edges (this 
          argument is passed to plt.hist as-is).
        * filename (None|str|PathLike): If None plot will be displayed otherwise it will
          not be displayed but instead saved to file specified by string or PathLike 
          object.
        * width (int): Width of plot in pixels.
        * height (int): For all methods except plot_actogram() it is height of plot in 
          pixels. For plot_actogram() it is height of subplots for each day, total plot 
          height will be height * [number of days to plot] plus top and bottom margins.
        * dpi (int): Resolution for displaying plot.
        
        Returns:
        --------------------------------------------------------------------------------
        None
        """
        bouts = self.activity_bouts(max_gap, min_duration, min_activity).astype('int')
        bout_starts = np.nonzero(np.diff(bouts, prepend=0, append=0, axis=-1) > 0)[0]
        bout_ends = np.nonzero(np.diff(bouts, prepend=0, append=0, axis=-1) < 0)[0]
        values = (bout_ends - bout_starts) * self.step.astype('int')
        graph_color = '#404040'
        if filename is not None:
            filename = Path(filename)
        nbins = 20
        fig = plt.figure(figsize=(width/dpi, height/dpi))
        plt.hist(values, bins=bins, color=graph_color)
        fig.text(0.5, 0.95, f"Bout length distribution {self.descr}", ha='center', fontsize=20, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    
    def activity_onset(self, step=None, percentile=20, N='6h', M='6h', bouts=False, mode='step'):
        """Calculate activity onset for each day.
        
        Activity onset for a given day is calculated as follows:
        1. Split day into intervals of uniform length (discretize it with some step).
        2. Denote all points where activity is less than some percentile of non-zero 
           activity as being inactive.
        3. Set activity values of all inactive points to -1 and all other points to 1.
        4. Apply convolution kernel with left part being negative and right part being 
           positive to activity values. This will smoothly summarize activity values.
        5. Find point with maximal summarized value. This will be activity onset.
        
        Arguments:
        --------------------------------------------------------------------------------
        * step (None|str|int|timedelta): Data discretization step used for calculations.
          None stands for self.max_gap, string interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * percentile (int): Percentile of daily non-zero activity to use as threshold 
          for activity onset calculation. Activity that is lower that this percentile 
          will be treated as zero activity.
        * N (str|int|timedelta): Length of period of negative values (daytime, left 
          part) in convolution kernel. String interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * M (str|int|timedelta): Length of period of positive values (nighttime, right 
          part) in convolution kernel. String interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        * mode: Defines shape of convolution kernel. Every kernel has discontinuity 
          where left and righ par connect (values around discontinuity are -1 and 1 for 
          left and right parts respectively). For kernels other than 'step' left part is
          decreasing from 0 to -1 and right part is decreasing from 1 to 0, i.e. parts 
          of kernel further from discontinuity are given less weight:
          - 'step': Kernel is step function with uniform left and right parts.
          - 'linear': Kernel value linearly function of relative distance to 
            discontinuity.
          - 'quadratic': Kernel value is quadratic function (square root) of relative 
            distance to discontinuity.
          - 'sine': Kernel value is proportional to shifted sine (cosine) of relative
            distance to discontinuity.
        
        Returns:
        --------------------------------------------------------------------------------
        * activity_onset (np.array[np.datetime64]): Activity onsets for each day. Note
          that returned array contains timestamps (absolute times of activity onset),
          not relative shifts from start of the day.
        """
        step, steps_per_day = self.__get_step(step)
        if bouts:
            values, timestamps = self.__discretize(self.bouts, step)
        else:
            values, timestamps = self.__discretize(self.activity, step)
        values = values.reshape(self.days, steps_per_day)
        N = pd.Timedelta(N).asm8.astype('<m8[m]') // step
        M = pd.Timedelta(M).asm8.astype('<m8[m]') // step
        if mode == 'step':    
            left = np.full(N, -1)
            right = np.full(M, 1)
        elif mode == 'linear':
            left = np.linspace(-1/N, -1, N)
            right = np.linspace(1, 1/M, M)
        elif mode == 'quadratic':
            left = -np.linspace(1/N, 1, N) ** 0.5
            right = np.linspace(1, 1/M, M) ** 0.5
        elif mode == 'sine':
            left = -np.sin(np.linspace(1/N, 1, N) * np.pi/2)
            right = np.sin(np.linspace(1, 1/M, M) * np.pi/2)
        else:
            raise ValueError(f'unrecognized mode')
        # If M != N, pad zeros to keep discontinuity at the center of kernel
        kernel = np.concatenate((np.zeros(max(M - N, 0)), left, right, np.zeros(max(N - M, 0))))
        result = np.zeros(self.days, dtype='<M8[m]')
        for d in range(self.days):
            tmp = values[d]
            if tmp.max() > 0:
                active = tmp >= np.percentile(tmp[tmp > 0], percentile, interpolation='higher')
            else:
                active = np.zeros(0, dtype='int')
            tmp[:] = -1
            tmp[active] = 1
            tmp = np.pad(tmp, steps_per_day, mode='constant', constant_values=-1)
            t = np.correlate(tmp, kernel, mode='same')[steps_per_day : 2 * steps_per_day]
            idx = steps_per_day - t[::-1].argmax() - 1
            result[d] = timestamps[d * steps_per_day + idx]
        return result
    
    
    def plot_activity_onset(self, step=None, percentile=20, N='6h', M='6h', bouts=False, mode='step',
                            filename=None, width=1000, height=600, dpi=100):
        """Calculate and plot activity onset for each day.
        
        Activity onsets for each day are plotted as shifts (in hours) from the start of
        the day (e.g. maximal possible value is 24).
        
        Activity onset for a given day is calculated as follows:
        1. Split day into intervals of uniform length (discretize it with some step).
        2. Denote all points where activity is less than some percentile of non-zero 
           activity as being inactive.
        3. Set activity values of all inactive points to -1 and all other points to 1.
        4. Apply convolution kernel with left part being negative and right part being 
           positive to activity values. This will smoothly summarize activity values.
        5. Find point with maximal summarized value. This will be activity onset.
        
        Arguments:
        --------------------------------------------------------------------------------
        * step (None|str|int|timedelta): Data discretization step used for calculations.
          None stands for self.max_gap, string interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * percentile (int): Percentile of daily non-zero activity to use as threshold 
          for activity onset calculation. Activity that is lower that this percentile 
          will be treated as zero activity.
        * N (str|int|timedelta): Length of period of negative values (daytime, left 
          part) in convolution kernel. String interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * M (str|int|timedelta): Length of period of positive values (nighttime, right 
          part) in convolution kernel. String interpreted as timedelta string, int 
          initerpreted as number of nanoseconds and timedelta used as-is.
        * bouts (bool): Flag, indicates whether calculation will be based on number of 
          activity events or on activity bouts. If bouts=True then at each time step 
          used value will be percentage of time when self.bouts=True and thus maximum 
          possible value for that step will be 1.
        * mode: Defines shape of convolution kernel. Every kernel has discontinuity 
          where left and righ par connect (values around discontinuity are -1 and 1 for 
          left and right parts respectively). For kernels other than 'step' left part is
          decreasing from 0 to -1 and right part is decreasing from 1 to 0, i.e. parts 
          of kernel further from discontinuity are given less weight:
          - 'step': Kernel is step function with uniform left and right parts.
          - 'linear': Kernel value linearly function of relative distance to 
            discontinuity.
          - 'quadratic': Kernel value is quadratic function (square root) of relative 
            distance to discontinuity.
          - 'sine': Kernel value is proportional to shifted sine (cosine) of relative
            distance to discontinuity.
        * filename (None|str|PathLike): If None plot will be displayed otherwise it will
          not be displayed but instead saved to file specified by string or PathLike 
          object.
        * width (int): Width of plot in pixels.
        * height (int): For all methods except plot_actogram() it is height of plot in 
          pixels. For plot_actogram() it is height of subplots for each day, total plot 
          height will be height * [number of days to plot] plus top and bottom margins.
        * dpi (int): Resolution for displaying plot.
        
        Returns:
        --------------------------------------------------------------------------------
        None
        """
        values = self.activity_onset(step, percentile, N, M, bouts, mode)
        values = ((values - self.__t0) % self.__day) / self.__hour
        fig = plt.figure(figsize=(width/dpi, height/dpi))
        plt.ylim(-1, 24)
        max_ticks = 20
        if filename is not None:
            filename = Path(filename)
        tick_step = self.days // (max_ticks - 1) + 1
        tick_mask = np.full(self.days, False, dtype='bool')
        for i in range(0, self.days, tick_step):
            tick_mask[i] = True
        tick_mask[-1] = True
        tick_pos = np.arange(self.days)[tick_mask]
        tick_labels = np.arange(self.start, self.stop, self.__day)[self.daily_mask][tick_mask].astype('datetime64[D]')
        plt.xticks(tick_pos, tick_labels, rotation=90)
        plt.plot(values)
        fig.text(0.5, 0.95, f"Activity Onset {self.descr}", ha='center', fontsize=20, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
            
            
def generate_data(points_per_day=100, days=10, activity_period='24h', night_period='24h', 
                  bg_ratio=0.2, multiactivity=False):
    rng = np.random.default_rng()
    start = pd.Timestamp('2020-01-01').asm8.astype('<M8[m]')
    activity_period = pd.Timedelta(activity_period).asm8.astype('<m8[m]')
    night_period = pd.Timedelta(night_period).asm8.astype('<m8[m]')
    minute = np.timedelta64(1, 'm')
    nbursts = rng.integers(1, 3, endpoint=True)
    activity_bursts = rng.integers(activity_period.astype('i8'), size=nbursts).astype('<m8[m]')
    
    # Generate activity
    time = np.zeros(points_per_day * days, dtype='<M8[ns]')
    value = np.ones(points_per_day * days, dtype='int')
    bg_size = int(points_per_day*bg_ratio)
    burst_size = points_per_day - bg_size
    for d in range(days):
        # Background activity
        background = start + rng.integers(activity_period.astype('i8'), size=bg_size)
        time[d*points_per_day : d*points_per_day+bg_size] = background
        # Activity bursts
        bursts = np.tile(activity_bursts, burst_size//activity_bursts.size+1)[:burst_size]
        bursts += (60*rng.normal(size=burst_size)).astype('<m8[m]')
        time[d*points_per_day+bg_size : (d+1)*points_per_day] = start + bursts
        if multiactivity:
            value[d*points_per_day+bg_size : (d+1)*points_per_day] += rng.integers(10, size=burst_size)
        d += 1
        start += activity_period
    sort = np.argsort(time)
    time = time[sort]
    value = value[sort]
    
    # Filter duplicate activity
    time, idx = np.unique(time, return_index=True)
    value = value[idx]
    
    # Generate night
    is_night = generate_night(time, night_period)
    
    return {'time': time, 'value': value, 'is_night': is_night}


def generate_night(timeseries, night_period='24h'):
    rng = np.random.default_rng()
    night_period = pd.Timedelta(night_period).asm8.astype('<m8[m]')
    is_night = np.ones(timeseries.size, dtype='bool')
    start = timeseries[0]
    stop = timeseries[-1]
    step = pd.Timedelta('5m').asm8
    nsteps = night_period / step
    d0 = pd.Timedelta(0).asm8
    marks = []
    while d0 < night_period:
        d1 = min(d0 + rng.integers(1, 100, endpoint=True) * step, night_period)
        marks.append([d0, d1])
        d0 = d1 + rng.integers(1, 100, endpoint=True) * step
    marks = np.array(marks)
    t0 = start
    t1 = t0 + marks[0, 1]
    mark_it = cycle(np.diff(marks, axis=0, append=(marks[0] + night_period).reshape(1, -1)))
    while t0 <= stop:
        indices = np.nonzero((timeseries >= t0) & (timeseries < t1))
        is_night[indices] = False
        d0, d1 = next(mark_it)
        t0 = t0 + d0
        t1 = t1 + d1
    return is_night