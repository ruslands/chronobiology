from pathlib import Path
from datetime import datetime, timedelta, tzinfo, timezone
from itertools import *

from influxdb import InfluxDBClient, DataFrameClient
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from collections.abc import Sequence

class DBQuery():
    """
    Class to access InfluxDB and get records from it.
    
    Initialisation:
    ---
    
    DBQuery(database, username, password, host='localhost', port=8086)
    * database -- Name of the database, string.
    * username -- Name of user, string.
    * password -- User password, string.
    * host -- IP adress, string. Optional.
    * port -- Connection port, int. Optional.
    
    Methods:
    ---
    
    get_tags(series)
    
    Returns list of all tags in the given series. 
    
    Arguments:
    * series -- Name of the series to access, string.
    
    ---
    
    get_fields(series)
    
    Returns list of all fields in the given series. 
    
    Arguments:
    * series -- Name of the series to access, string.
    
    ---
    
    get_keys(series, key)
    
    Returns list of all key (tag) values for a given key (tag) for which there is at least one record in the 
      given series. 
    
    Arguments:
    * series -- Name of the series to access, string.
    * key -- Name of the key, string.
    
    ---
    
    get_data(series, fields, keys=None, start=None, stop=None, local_tz=False)
    
    Selects timestamps and given fields/tags from series where tag specified by key is equal to val.
    
    Returns dictionary of numpy arrays with keys being 'time' for timestamps and whatever field names
      are passed in the fields arg.
    
    Supports optional specification of start and/or end timestamps/dates.
    
    Arguments:
    * series -- Name of the series, string.
    * fields -- Name(s) of the fields in series. Can be non-empty string, list/tuple/set of strings or dict with 
      keys being field names and values being numpy types (or type names) of return arrays for that field.
      Pass None as type to use autodetection from table data. Pass '*' to select all fields and tags.
    * keys -- None or dictionary of key: value pairs to use in query WHERE clause. Only records for which tags with
      names specified by keys have (one of) corresponding values will be selected. If None or empty dict then 
      records won't be filtered based on tag values. If for some key value is a list, tuple or set then records with
      tags having one of those values will be selected (they will be joined by OR). Optional.
    * start -- Inclusive lower time boundary for returned data. Only records with time >= start will be returned.
      None indicates no lower boundary. String, int or any other type which can be convetred do datetime. Optional.
    * stop -- Exclusive upper time boundary for returned data. Only records with time < stop will be returned.
      None indicates no upper boundary. String, int or any other type which can be convetred do datetime. Optional.
    * local_tz -- Indicates whether user uses local time ot UTC time in their code. InfluxDb is assumed to always 
      hold timestamps in UTC. If True then all timezone correction will be applied to start and stop arguments and
      to all returned timestamps. Boolean. Optional.
    
    Example usage:
    ---
    
    q = DBQuery("MyDatabase", "user", "password", host="186.12.1.4", port=8000)
    
    q.get_tags('series1')
    >> ['tag1', 'tag2']
    
    q.get_fields('series1')
    >> ['value']
    
    q.get_keys('series1', 'tag1')
    >> ['foo', 'bar']
    
    # Use '*' to select all fields/tags
    q.get_data('series1', '*')
    >> {'time': array(['2019-11-05T00:00:00.000000000', '2019-11-05T06:00:00.000000000', 
    ...                '2019-11-06T00:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'key1': array(['foo', 'bar', 'foo'], dtype='<U3'),
    ... 'key2': array(['1', '2', '3'], dtype='<U1'),
    ... 'value': array([1.0, 1.5, 2.0], dtype=float64)}
    
    # start is inclusive
    q.get_data('series1', 'value', start='2019-11-05 06:00')
    >> {'time': array(['2019-11-05T06:00:00.000000000', '2019-11-06T00:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'value': array([1.5, 2.0], dtype=float64)}
    
    # stop is exclusive
    q.get_data('series1', ['value', 'key1'], stop='2019-11-06')
    >> {'time': array(['2019-11-05T00:00:00.000000000', '2019-11-05T06:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'value': array([1.0, 1.5], dtype=float64),
    ... 'key1': array(['foo', 'bar'], dtype='<U3')}
    
    # Specify key value
    q.get_data('series1', '*', {'key1': 'foo'})
    >> {'time': array(['2019-11-05T00:00:00.000000000', '2019-11-06T00:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'key1': array(['foo', 'foo'], dtype='<U3'),
    ... 'key2': array(['1', '3'], dtype='<U1'),
    ... 'value': array([1.0, 2.0], dtype=float64)}
    
    # Specify multiple values for one key and use autoconversion to string
    q.get_data('series1', 'value', {'key2': [1, 2]})
    >> {'time': array(['2019-11-05T00:00:00.000000000', '2019-11-05T06:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'key1': array(['foo', 'bar'], dtype='<U3'),
    ... 'key2': array(['1', '2'], dtype='<U1'),
    ... 'value': array([1.0, 1.5], dtype=float64)}
    
    # Specify multiple keys
    q.get_data('series1', 'value', {'key1': 'foo', 'key2': [1, 2]})
    >> {'time': array(['2019-11-05T00:00:00.000000000'], dtype='datetime64[ns]'),
    ... 'key1': array(['foo'], dtype='<U3'),
    ... 'key2': array(['1'], dtype='<U1'),
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
    
    
    def get_tags(self, series):
        query = f'SHOW TAG KEYS FROM "{series}";'
        return [x[0] for x in self.client.query(query).raw['series'][0]['values']]
    
    
    def get_fields(self, series):
        query = f'SHOW FIELD KEYS FROM "{series}";'
        processed_query = self.client.query(query).raw['series'][0]['values']
        return [x[0] for x in processed_query]
    
    
    def get_keys(self, series, key):
        query = f'SHOW TAG VALUES FROM "{series}" WITH KEY = "{str(key)}";'
        return [x[1] for x in self.client.query(query).raw['series'][0]['values']]
    
    
    def get_data(self, series, fields, keys=None, start=None, stop=None, local_tz=False):
        
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
        type_conversion = {'integer': 'int64', 'float': 'float64', 'string': 'O', 'boolean': 'bool'}
        ftypes = {'time': time_type}
        query = f'SHOW TAG KEYS FROM "{series}";'
        for f in self.client.query(query).raw['series'][0]['values']:
            ftypes[f[0]] = np.dtype(type_conversion['string'])
        query = f'SHOW FIELD KEYS FROM "{series}";'
        for f in self.client.query(query).raw['series'][0]['values']:
            ftypes[f[0]] = np.dtype(type_conversion[f[1]])
        if type(fields) is dict:
            _fields = []
            for f, t in fields.items():
                if f == '*':
                    _fields += [f]
                else:
                    if t is not None:
                        ftypes[f] = np.dtype(t)
                    _fields += [f'"{f!s}"']
            fields = _fields
        elif type(fields) in (list, tuple, set):
            fields = [f if f == '*' else f'"{f!s}"' for f in fields]
        elif type(fields) is str:
            fields = [fields] if fields == '*' else [f'"{fields!s}"']
        else:
            raise TypeError(f"fields should be a string, list, tuple, set or dict but {type(fields)} was passed")
        if len(fields) == 0:
            raise ValueError(f"fields should be non-empty")
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
        query = f'SELECT {", ".join(fields)} FROM "{series}"{where_clause}{time_query};'
        processed_query = self.client.query(query)
        data = processed_query.raw['series'][0]['values']
        fields = processed_query.raw['series'][0]['columns']
        result = {}
        for field in fields:
            result[field] = np.zeros(len(data), dtype=ftypes[field])
        for i, row in zip(count(), data):
            for value, field in zip(row, fields):
                result[field][i] = _type_cast(value, ftypes[field])
        for field in fields:
            if ftypes[field] == np.dtype('O'):
                result[field] = result[field].astype('U')
        return result

class CycleAnalyzer():
    """
    Class to analyze circadian cycles given timestamp data.
    
    Initialisation:
    ---
    
    CycleAnalyzer(timeseries, night=('18:00', '06:00'), step='5m', start=None, stop=None, descr='',
                  max_gap='1m', min_duration='0m', *, min_count=2, activity_threshold=1)
    * timeseries -- numpy 1D array of timestamps of type '<M8[ns]' (numpy.datetime64 with 'ns' precision). This 
      timeseries should represent activity events.
    * night -- Sequence of night interval start and stop boundaries or sequence of such sequences for each day.
      Night boundaries can be given as integer (nanoseconds) or as a string in one of the following formats: 'H', 
      'HH', 'H:MM', 'HH:MM' ('6', '06', '6:00' and '06:00' indicate same time). Overall number of night boundaries
      should be even and it is assumed that after night start boundary next item will indicate night end boundary. 
      The timestamp for the last boundary for the day can be less than previous and that indicates wrapping around 
      day boundary: ('18:00', '06:00') means that intervals from 18:00 to 24:00 on the current day and interval 
      from 00:00 to '06:00' on the next day are treated as night. If only one night sequence provided then this 
      sequence will be used for all days. To provide different night intervals for each day use the following form:
      night=([day1_night1_b1, day1_night1_b2, day1_night2_b1, ...], [day2_night1_b1, ...], ... [dayn_night1_b1, ...]).
      When night is specified for each day the number of night boundaries for some of the days can be odd given that 
      overall number of boundaries is even. For example this is valid: night=(['22'], ['04', '20'], ['04', '18', '24']).
      Any of '0', '0:00', '00', '00:00', '24' or '24:00' can be used to indicate end of the day. Optional.
    * step -- Default discretization step. If method uses discretization and discretization step is not specified for
      that method call then this value will be used for all such methods invoked from this instance. String, integer, 
      timedelta or any other type which can be converted to timedelta.
    * start -- Inclusive lower time boundary for returned data. Only records with time >= start will be returned.
      None indicates no lower boundary. String, int or any other type which can be convetred do datetime. Optional.
    * stop -- Exclusive upper time boundary for returned data. Only records with time < stop will be returned.
      None indicates no upper boundary. String, int or any other type which can be convetred do datetime. Optional.
    * descr -- Textual description that will be added to the end of plot headings. Can be used to specify the 
      source of timeseries data on the plots (for example to specify what specimen(s) was used to generate timeseries).
      Optional.
    * max_gap -- Maximal gap between two consecutive activity events to treat them as belonging to the same activity 
      bout. String, integer, timedelta or any other type which can be converted to timedelta.
    * min_duration -- Minimal duration of activity bout to consider it as valid. String, integer, timedelta or any 
      other type which can be converted to timedelta.
    * min_count -- Minimal count of activity events in the activity bout to consider it valid. Values less than 2 will
      lead to possibility of activity bouts with 0 duration (if min_duration is 0), so they are not recommended. 
      Integer.
    * activity_threshold -- Minimum number of activity events in a day to consider that day in analysis. Used to filter out 
      days when experiment was not going or when activity was not large enough for valid analysis.
    
    Attributes:
    ---
    
    * start -- Lower time boundary to analyze. If start is passed during class initialisation it will be equal to that
      value, otherwise it will be start of the day of the first activity record (i.e. if first record has timestamp 
      '2020-01-01 01:05' then start will be equal to '2020-01-01 00:00:00.' if explicit start value is not passed to 
      the constructor). numpy.dtype('datetime64[ns]').
    * stop -- Adjusted upper boundary to analyze. Adjustment made by increasing stop argument passed to instance 
      constructor in such a way that difference between start and stop timestamps constitutes whole number of days. 
      numpy.numpy.dtype('datetime64[ns]').
    Note 1:
      Despite this adjustment the data with timestamps larger than original stop timestamp that was passed to class 
      constructor will never be included (i.e. if class is initialized with start='2020-01-01 06:00' and 
      stop='2020-02-02 18:00' then adjusted stop value will be '2020-02-03 06:00' but timestamps older than 
      '2020-02-02 18:00' will not be included even if they are present in original timeseries).
    * activity -- Property that return all activity events that was selected during class initialisation and wasn't
      filtered out due to low daily activity. Its value will change if data will be refiltered. numpy.array with
      shape=(?,) and dtype='datetime64[ns]' (? in shape indicates any value).
    * bouts -- Precalculated bouts to be used in class methods when bouts=True is passed to them. numpy.array with
      shape=(?, 2) and dtype='datetime64[ns]'. bouts[:, 0] hold bout start timestamps and bouts[:, 1] hold bout 
      end timestamps.
    * step -- Default discretization step that will be used for methods of this class. numpy.timedelta64.
    * descr -- Text that will be prepended to all plot headings. String.
    * total_days -- Total number of days (including those that were filtered out) between start and stop timestamps.
      Integer.
    * mask -- numpy boolean 1D array of length total_days. Holds True for days that wasn't filteret and False for 
      filtered out days. numpy.array with shape=(total_days,) and dtype='bool'.
    * days -- Number of days that wasn't filtered out due to low activity, days=mask.sum(). Integer.
    * day_indices -- numpy 2D array day indices which indicates starts (inclusive) and ends (exclusive) of 
      consecutive non-foltered day intervals. day_indices[:, 0] holds starting day indices and day_indices[:, 0]
      holds ending day indices. If n is length of day_indices 1st dimension then for any A<n it will be true that
      mask[day_indices[A, 0] : day_indices[A, 1]] will hold only True values, and all mask values that don't fall 
      between day_indices[S, 0] (inclusive) and day_indices[S, 1] (exclusive) for some S will be False. Put another
      way np.hstack([np.arange(s, e) for [s, e] in day_indices]) will return indices of all mask values that are True.
    * activity_threshold -- Minimal number of activity events in a day to consider it in an analysis. Integer.
    * night -- list of numpy 2D arrays of night interval start and end times expressed as hours. Length of list is
      equal to total_days. Shape of numpy arrays for each day is (?, 2) where first axis can vary between days 
      (different days can have different number of night intervals) but for day d night[d][:, 0] hold start times 
      for that days' night intervals (expressed as offset from the beginning of calendar day) and night[d][:, 1] 
      hold end times for that days' night intervals (expressed in the same way). List of numpy.array with 
      shape=(?, 2) and dtype='timedelta64[ns]'.
    
    Methods:
    ---
    
    Most methods can base their analysis on either activity events or precalculated activity bouts. All such methods 
    accept optional bouts argument.
    
    plot_* methods should be used to plot data. All such methods accept following arguments:
    * width -- Width of plot in pixels. Defaults to 1000.
    * height -- For all methods except plot_actogram() it is height of plot in pixels and defaults to 600.
      For plot_actogram() it is height of subplots for each day -- total plot height will depend on number of days 
      to plot -- and defaults to 100.
    * filename -- None, string or Path. If None plot will be displayed otherwise it will not be displayed but instead
      saved to specified file. Defaults to None.
    * dpi -- resolution for displaying plot. Defaults to 96.
    
    ---
    
    select_dates(start=None, stop=None, bouts=False)
    
    Returns activity events (bouts=False) or activity bouts (bouts=True) that fall between specified start (inclusive) 
    and stop (exclusive) timestamps. Does not include activity that was filtered out by mask.
    
    Timeseries can be either 1D array of datetimes or 2D array of dateteimes with second dimension equal to 2 in which
    case it is treated as array of time intervals (intervals begin at timeseries[:, 0] and end at timeseries[:, 1]).
    
    Arguments:
    * start -- Inclusive lower time boundary for returned data. Only records with time >= start will be returned.
      None indicates no lower boundary. String, int or any other type which can be convetred do datetime. Optional.
    * stop -- Exclusive upper time boundary for returned data. Only records with time < stop will be returned.
      None indicates no upper boundary. String, int or any other type which can be convetred do datetime. Optional.
    * bouts -- Flag that indicates whether values from activity events or activity bouts will be returned. Bool.
    
    ---
    
    filter_inactive(activity_threshold=1)
    
    Refilters days based on new minimal activity. All subsequent method calls will use new filtered days. Returns None.
    
    Arguments:
    * activity_threshold -- minimum number of activity events in a day to consider that day in analysis. Used to filter out 
      days when experiment was not going or when activity was not large enough for valid analysis. Integer.
    
    ---
    
    activity_bouts(max_gap='1m', min_duration='0m', min_count=2):
    
    Returns activity bouts calculated from self.activity using provided parameters. Does not unpdate self.bouts -- 
    use adjust_bouts() for that.
    
    Arguments:
    * max_gap -- Maximal gap between two consecutive activity events to treat them as belonging to the same activity 
      bout. String, integer, timedelta or any other type which can be converted to timedelta.
    * min_duration -- Minimal duration of activity bout to consider it as valid. String, integer, timedelta or any 
      other type which can be converted to timedelta.
    * min_count -- Minimal count of activity events in the activity bout to consider it valid. Values less than 2 will
      lead to possibility of activity bouts with 0 duration (if min_duration is 0), so they are not recommended.
      Integer.
    
    ---
    
    adjust_bouts(max_gap='1m', min_duration='0m', min_count=2):
    
    Recalculates activity bouts based on self.activity using provided parameters and updates self.bouts. Returns None.
    
    Intended to be used to update activity bouts used by other methods.
    
    Arguments:
    * max_gap -- Maximal gap between two consecutive activity events to treat them as belonging to the same activity 
      bout. String, integer, timedelta or any other type which can be converted to timedelta.
    * min_duration -- Minimal duration of activity bout to consider it as valid. String, integer, timedelta or any 
      other type which can be converted to timedelta.
    * min_count -- Minimal count of activity events in the activity bout to consider it valid. Values less than 2 will
      lead to possibility of activity bouts with 0 duration (if min_duration is 0), so they are not recommended.
      Integer.
    
    ---
    
    discretize(step=None, bouts=False)
    
    Groups activity events (bouts=False) or activity bouts (bouts=True) in the bins of size step. Bins span time period
    between self.start and self.stop. Returns tuple of numpy 1D arrays: first of them represents bin starting times 
    (dtype='datetime64[ns]') and second represents event counts for each bin (bouts=False, dtype='int64') or activity 
    coverage represented as floats between 0.0 and 1.0, inclusive (bouts=True, dtype='float64').
    
    When bouts=True activity coverage is calculated as ratio of overlapping between bin time intervals and activity 
    bouts time intervals. For example, if there are 3 activity bouts (['01:30', '03:00'], ['04:30', '06:00'] and 
    ['16:00', '27:00']), step='5 minutes' and discretization  then there will be 6 bins with start times ['00:00', 
    '05:00', '10:00', '15:00', '20:00', '25:00']; first bout overlaps only 1st bin and amount of overlap is 1.5 minutes, 
    second bout overlaps 1st and 2nd bins and amounts of overlap are 0.5 and 1 minute, third bout overlaps 4th, 5th and 
    6th bins and amounts of overlap are 4, 5 and 2 minutes; coverage for bins will be [(1.5+0.5)/5, 1/5, 0/5, 4/5, 5/5, 
    2/5] = [0.4, 0.2, 0.0, 0.8, 1.0, 0.4]
    
    Arguments:
    * step -- Bin size, if None instance defaul step will be used. None or string, integer, timedelta or any other type 
    which can be converted to timedelta.
    * bouts -- Flag that indicates whether discrtetization will be based on activity events or activity bouts. Bool.
    
    ---
    
    plot_actogram(step=None, bouts=True, width=1000, height=100, filename=None, dpi=96)
    
    Plots double actogram with right half shifted by 1 day. Night intervals for each day are also plotted on actogram.
    
    Uses activity bouts by default to give prettier looking actogram.
    
    Arguments:
    * step -- Bin size, if None instance default step will be used. None or string, integer, timedelta or any other type 
      which can be converted to timedelta.
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    * filename -- Name of the file to save plot to. If None plot will be displayed instead.
    * width -- Plot width in pixels.
    * height -- Plot height in pixels.
    * dpi -- plot DPI.
    
    ---
    
    periodogram(step=None, min_period='16h', max_period='32h', bouts=False)
    
    Calculates periodogram powers and returns tuple of numpy 1d arrays first of which is time periods between min_period 
    and max_period (inclusive) and second is periodogram powers for each period. If periods, powers = periodogram() then 
    periods[powers.argmax()] will return period with maximal periodogram power.
    
    Arguments:
    * step -- Step size for generating periods, if None instance default step will be used. None or string, integer, 
      timedelta or any other type which can be converted to timedelta.
    * min_period -- Minimal period length, inclusive. String, integer, timedelta or any other type which can be 
      converted to timedelta.
    * max_period -- Maximal period length, inclusive. String, integer, timedelta or any other type which can be 
      converted to timedelta.
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    
    ---
    
    plot_periodogram(step=None, min_period='16h', max_period='32h', bouts=False, 
                     filename=None, width=1000, height=600, dpi=96)
    
    Calculates and plots periodogram powers. Plot also includes indication of period with maximal periodogram power.
    
    Arguments:
    * step -- Step size for generating periods, if None instance default step will be used. None or string, integer, 
      timedelta or any other type which can be converted to timedelta.
    * min_period -- Minimal period length, inclusive. String, integer, timedelta or any other type which can be 
      converted to timedelta.
    * max_period -- Maximal period length, inclusive. String, integer, timedelta or any other type which can be 
      converted to timedelta.
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    * filename -- Name of the file to save plot to. If None plot will be displayed instead.
    * width -- Plot width in pixels.
    * height -- Plot height in pixels.
    * dpi -- Plot DPI.
    
    ---
    
    light_activity(bouts=False)
    
    Calculates light phase activity and returns tuple (daily, total) where daily is numpy array with shape=(self.days,)
    which holds light phase activity calculated for each day and total is light phase activity calculated on data for 
    all days (in general total != daily.mean()).
    
    Arguments:
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    
    ---
    
    plot_light_activity(bouts=False, filename=None, width=1000, height=600, dpi=96)
    
    Calculates and plots light phase activity for each day. Plot also includes value based on data for all days.
    
    Arguments:
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    * filename -- Name of the file to save plot to. If None plot will be displayed instead.
    * width -- Plot width in pixels.
    * height -- Plot height in pixels.
    * dpi -- Plot DPI.
    
    ---
    
    interdaily_stability(step=None, bouts=False)
    
    Calculates and returns interdaily stability. Returned value is a single float in range [0, 1], inclusive.
    
    Arguments:
    * step -- Step size for generating periods, if None instance default step will be used. None or string, integer, 
      timedelta or any other type which can be converted to timedelta.
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    
    ---
    
    intradaily_variability(step=None, bouts=False)
    
    Calculates intradaily variability and returns tuple (daily, total) where daily is numpy array with 
    shape=(self.days,) which holds intradaily variability calculated for each day and total is intradaily variability 
    calculated on data for all days (in general total != daily.mean()).
    
    Arguments:
    * step -- Step size for generating periods, if None instance default step will be used. None or string, integer, 
      timedelta or any other type which can be converted to timedelta.
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    
    ---
    
    plot_intradaily_variability(step=None, bouts=False, filename=None, width=1000, height=600, dpi=96)
    
    Calculates and plots intradaily variability for each day. Plot also includes value based on data for all days.
    
    Arguments:
    * step -- Step size for generating periods, if None instance default step will be used. None or string, integer, 
      timedelta or any other type which can be converted to timedelta.
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    * filename -- Name of the file to save plot to. If None plot will be displayed instead.
    * width -- Plot width in pixels.
    * height -- Plot height in pixels.
    * dpi -- Plot DPI.
    
    ---
    
    relative_amplitude(step=None, most_active='10h', least_active='5h', bouts=False)
    
    Calculates relative amplitude and returns tuple (daily, total) where daily is numpy array with 
    shape=(self.days,) which holds relative amplitude calculated for each day and total is relative amplitude 
    calculated on data for all days (in general total != daily.mean()).
    
    Arguments:
    * step -- Step size for generating periods, if None instance default step will be used. None or string, integer, 
      timedelta or any other type which can be converted to timedelta.
    * most_active -- Length of most active period. String, integer, timedelta or any other type which can be 
      converted to timedelta.
    * least_active -- Length of least active period. String, integer, timedelta or any other type which can be 
      converted to timedelta.
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    
    ---
    
    plot_relative_amplitude(step=None, most_active='10h', least_active='5h', bouts=False, 
                            filename=None, width=1000, height=600, dpi=96)
    
    Calculates and plots relative amplitude for each day. Plot also includes value based on data for all days.
    
    Arguments:
    * step -- Step size for generating periods, if None instance default step will be used. None or string, integer, 
    timedelta or any other type which can be converted to timedelta.
    * most_active -- Length of most active period. String, integer, timedelta or any other type which can be 
      converted to timedelta.
    * least_active -- Length of least active period. String, integer, timedelta or any other type which can be 
      converted to timedelta.
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    * filename -- Name of the file to save plot to. If None plot will be displayed instead.
    * width -- Plot width in pixels.
    * height -- Plot height in pixels.
    * dpi -- Plot DPI.
    
    ---
    
    daily_bouts(max_gap=None, min_duration=None, min_count=None, timescale='1s'):
    
    Calculates activity bouts based on provided parameters and then for each day calculates number of activity bouts 
    and average activity bout duration. Returns tuple (bout_counts, bout_durations) where bout_counts and bout_durations
    are numpy 1D arrays.
    
    If some of max_gap, min_duration or min_count is None then values provided during class initialization or in a last
    call to adjust_bouts() will be used.
    
    Arguments:
    * max_gap -- Maximal gap between two consecutive activity events to treat them as belonging to the same activity 
      bout. None, string, integer, timedelta or any other type which can be converted to timedelta.
    * min_duration -- Minimal duration of activity bout to consider it as valid. None, string, integer, timedelta or any 
      other type which can be converted to timedelta.
    * min_count -- Minimal count of activity events in the activity bout to consider it valid. Values less than 2 will
      lead to possibility of activity bouts with 0 duration (if min_duration is 0), so they are not recommended.
      None or integer.
    * timescale -- Timescale of bout durations. Bout durations will be calculated in nanoseconds and then divided by this
      parameter. String, integer, timedelta or any other type which can be converted to timedelta.
      
    ---
    
    plot_daily_bouts(max_gap=None, min_duration=None, min_count=None, timescale='1s', 
                     filename=None, width=1000, height=600, dpi=96)
    
    Calculates and plots number of activity bouts and average bout duration for each day. Bout counts pplotted as bar plot
    on left y-axis and average bout durations plotted as line plot on right y-axis.
    
    If some of max_gap, min_duration or min_count is None then values provided during class initialization or in a last
    call to adjust_bouts() will be used.
    
    Arguments:
    * max_gap -- Maximal gap between two consecutive activity events to treat them as belonging to the same activity 
      bout. None, string, integer, timedelta or any other type which can be converted to timedelta.
    * min_duration -- Minimal duration of activity bout to consider it as valid. None, string, integer, timedelta or any 
      other type which can be converted to timedelta.
    * min_count -- Minimal count of activity events in the activity bout to consider it valid. Values less than 2 will
      lead to possibility of activity bouts with 0 duration (if min_duration is 0), so they are not recommended.
      None or integer.
    * timescale -- Timescale of bout durations. Bout durations will be calculated in nanoseconds and then divided by this
      parameter. String, integer, timedelta or any other type which can be converted to timedelta.
    * filename -- Name of the file to save plot to. If None plot will be displayed instead.
    * width -- Plot width in pixels.
    * height -- Plot height in pixels.
    * dpi -- Plot DPI.
    
    ---
    
    plot_bout_histogram(max_gap=None, min_duration=None, min_count=None, timescale='1s', bins=20,
                        filename=None, width=1000, height=600, dpi=96)
    
    Calcultes activity bouts based on provided parameters and plots histogram of their duration distribution.
    
    If some of max_gap, min_duration or min_count is None then values provided during class initialization or in a last
    call to adjust_bouts() will be used.
    
    Arguments:
    * max_gap -- Maximal gap between two consecutive activity events to treat them as belonging to the same activity 
      bout. None, string, integer, timedelta or any other type which can be converted to timedelta.
    * min_duration -- Minimal duration of activity bout to consider it as valid. None, string, integer, timedelta or any 
      other type which can be converted to timedelta.
    * min_count -- Minimal count of activity events in the activity bout to consider it valid. Values less than 2 will
      lead to possibility of activity bouts with 0 duration (if min_duration is 0), so they are not recommended.
      None or integer.
    * timescale -- Timescale of bout durations. Bout durations will be calculated in nanoseconds and then divided by this
      parameter. String, integer, timedelta or any other type which can be converted to timedelta.
    * bins -- Number of bins in a histogram. This argument will be passed to pyplot.hist so it can be an integer or a 
      sequence of bin start and end times.
    * filename -- Name of the file to save plot to. If None plot will be displayed instead.
    * width -- Plot width in pixels.
    * height -- Plot height in pixels.
    * dpi -- Plot DPI.
    
    ---
    
    activity_onset(step=None, percentile=20, N=6, M=6, bouts=False)
    
    Calculates activity onset for each day. Returns numpy array with shape=(self.days,) and dtype='datetime64[ns]'.
    
    Note that array returned by this function is timestamps (i.e. they include date) not timedeltas (offsets for each day).
    
    Arguments:
    * step -- Step size for generating periods, if None instance default step will be used. None or string, integer, 
      timedelta or any other type which can be converted to timedelta.
    * percentile -- Defines which percentile of daily non-zero activity will be considered as potential candidate for 
      activity onset. Integer.
    * N -- Determines length of period of -1's in convolution kernel. String, integer, timedelta or any other type which 
      can be converted to timedelta.
    * M -- Determines length of period of 1's in convolution kernel. String, integer, timedelta or any other type which 
      can be converted to timedelta.
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    
    ---
    
    plot_activity_onset(step=None, percentile=20, N='6h', M='6h', bouts=False, 
                        filename=None, width=1000, height=600, dpi=96)
    
    Calculates and plots activity onset for each day.
    
    Arguments:
    * step -- Step size for generating periods, if None instance default step will be used. None or string, integer, 
      timedelta or any other type which can be converted to timedelta.
    * percentile -- Defines which percentile of daily non-zero activity will be considered as potential candidate for 
      activity onset. Integer.
    * N -- Determines length of period of -1's in convolution kernel. String, integer, timedelta or any other type which 
      can be converted to timedelta.
    * M -- Determines length of period of 1's in convolution kernel. String, integer, timedelta or any other type which 
      can be converted to timedelta.
    * bouts -- Flag that indicates whether calculation will be based on activity events or activity bouts. Bool.
    * filename -- Name of the file to save plot to. If None plot will be displayed instead.
    * width -- Plot width in pixels.
    * height -- Plot height in pixels.
    * dpi -- Plot DPI.
    """

    # Time constants used in class methods
    __t0 = pd.Timestamp(0).asm8
    __zero = pd.Timedelta(0).asm8
    __day = pd.Timedelta('1d').asm8
    __hour = pd.Timedelta('1h').asm8
    
    
    def __init__(self, timeseries, night=('18:00', '06:00'), step='5m', start=None, stop=None, descr='',
                 max_gap='1m', min_duration='0m', *, min_count=2, activity_threshold=1):        
        self.__activity = __class__.__select_dates(timeseries, start=start, stop=stop)
        self.__adjust_start_stop(start=start, stop=stop)
        self.step = step
        self.step = self.__get_step(step)
        self.__max_gap = max_gap
        self.__min_duration = min_duration
        self.__min_count = min_count
        self.descr = descr
        self.total_days = (self.stop - self.start) // self.__day
        self.mask = np.full(self.total_days, True, dtype='bool')
        self.filter_inactive(activity_threshold=activity_threshold)
        
        def _seq_stat(seq):
            """
            Returns number of dimensions (nesting depth) and size (number of leaf elements) of a compound sequence.

            Raises error if sequence nesting depth is inconsistent (i.e. at some depth exist both atominc and 
            sequential elements).
            """

            def _is_atom(x):
                return isinstance(x, str) or not isinstance(x, Sequence)

            def _helper(seq, curr_depth, max_depth, size, final):
                curr_depth += 1
                if max_depth < curr_depth:
                    if final:
                        raise ValueError(f"sequence has inconsistent nesting")
                    else:
                        max_depth = curr_depth
                atoms = None
                for el in seq:
                    if _is_atom(el):
                        size += 1
                        if atoms is False:
                            raise ValueError(f"sequence has inconsistent nesting")
                        if curr_depth < max_depth:
                            raise ValueError(f"sequence has inconsistent nesting")
                        atoms = True
                        final = True
                    else:
                        if atoms is True:
                            raise ValueError(f"sequence has inconsistent nesting")
                        atoms = False
                        max_depth, size, final = _helper(el, curr_depth, max_depth, size, final)
                return max_depth, size, final

            if seq is None:
                return 0, 0
            elif _is_atom(seq):
                return 0, 1
            else:
                max_depth, size, _ = _helper(seq, 0, 0, 0, False)
            return max_depth, size
        
        def _get_hour(t):
            if isinstance(t, np.timedelta64):
                return t % self.__day
            if ':' not in t:
                t = t + ':00'
            if t == '24:00':
                return self.__day
            else:
                return ((pd.Timestamp(t).asm8 - self.__t0) % self.__day)
        
        ndim, size = _seq_stat(night)
        if size % 2 != 0 or ndim > 2 or (ndim == 2 and (len(night) != self.total_days)):
            print(size, len(night), self.total_days)
            raise ValueError(f"night should be list/tuple with even number of elements "
                             f"that specifies start and end of night periods for all days or "
                             f"sequence of such lists/tuples for each day")
        if size == 0:
            night_pos = np.empty((0, 2), dtype='<m8[ns]')
            self.night = [night_pos] * self.total_days
        elif ndim == 1:
            night_pos = [_get_hour(t) for t in night]
            last = self.__zero
            for i in range(0, len(night_pos) - 2, 2):
                if night_pos[i+1] < night_pos[i] or night_pos[i] < last:
                    raise ValueError(f"overlapping night intervals")
                last = night_pos[i+1]
            if night_pos[-2] < last:
                raise ValueError(f"overlapping night intervals")
            if night_pos[-1] == self.__zero:
                night_pos[-1] = self.__day
            if night_pos[-1] < night_pos[-2]:
                if night_pos[1] < night_pos[-1]:
                    raise ValueError(f"overlapping night intervals")
                else:
                    night_pos = [self.__zero] + [night_pos[-1]] + night_pos[:-1] + [self.__day]
            night_pos = np.array(night_pos).reshape(-1, 2)
            self.night = [night_pos] * self.total_days
        else:
            self.night = [None] * self.total_days
            night_pos = [[_get_hour(t) for t in d] for d in night]
            night_pos.append([])
            odd = False
            for d in range(self.total_days):
                n = len(night_pos[d])
                if n == 0:
                    self.night[d] = np.empty((0, 2), dtype='<m8[ns]')
                    continue
                if n >= 2:
                    if night_pos[d][-1] < night_pos[d][-2]:
                        night_pos[d+1] = [night_pos[d][-1]] + night_pos[d+1]
                        night_pos[d] = night_pos[d][:-1]
                        n -= 1
                last = self.__zero
                for i in range(0, n - 1, 2):
                    if night_pos[d][i+1] < night_pos[d][i] or night_pos[d][i] < last:
                        raise ValueError(f"overlapping night intervals")
                    last = night_pos[d][i+1]
                if night_pos[d][-1] == self.__zero:
                        night_pos[d][-1] = self.__day
                if n%2 != 0:
                    if odd:
                        night_pos[d] = [self.__zero] + night_pos[d]
                        odd = False
                    else:
                        night_pos[d] = night_pos[d] + [self.__day]
                        odd = True
                else:
                    if odd:
                        night_pos[d] = [self.__zero] + night_pos[d] + [self.__day]
                self.night[d] = np.array(night_pos[d]).reshape(-1, 2)
    
    
    @property
    def activity(self):
        res = []
        for b in self.day_indices:
            res.append(__class__.__select_dates(self.__activity, 
                                              start=(self.start + b[0] * self.__day), 
                                              stop=(self.start + b[1] * self.__day)))
        return np.hstack(res)
    
    
    def __get_step(self, step=None):
        if step is None:
            step = self.step
        return pd.Timedelta(step).asm8
    
    
    def __get_step_spd(self, step=None):
        step = self.__get_step(step)
        if self.__day % step:
            raise ValueError(f"there should be whole number of steps in 1 day")
        steps_per_day = self.__day // step
        if steps_per_day == 0:
            raise ValueError(f"step can't be larger that 1 day")
        return step, steps_per_day

    @staticmethod
    def __select_dates(timeseries, start=None, stop=None):
        if start is None and stop is None:
            return timeseries
        if start is None:
            start = pd.Timestamp.min.asm8
        else:
            start = pd.Timestamp(start).asm8
        if stop is None:
            stop = pd.Timestamp.max.asm8
        else:
            stop = pd.Timestamp(stop).asm8
        if timeseries.ndim == 1:
            if timeseries.size > 0:
                indexes = np.argwhere((timeseries >= start) & (timeseries < stop)).ravel()
            else:
                indexes = np.array([], dtype='i8')
            return timeseries[indexes]
        elif timeseries.ndim == 2 and timeseries.shape[1] == 2:
            if timeseries.size > 0:
                indexes = np.argwhere((timeseries[:, 1] >= start) & (timeseries[:, 0] < stop)).ravel()
            else:
                indexes = np.empty((0, 2), dtype='i8')
            result = timeseries[indexes]
            if result.size:
                result[0, 0] = np.maximum(result[0, 0], start)
                result[-1, 1] = np.minimum(result[-1, 1], stop - 1)
            return result
        else:
            raise ValueError(f"first argument should be 1-D array of consecutive timestamps (represents" 
                             " event times), or 2-D array of consecutive timestamps with shape (N, 2)"
                             " (represents non-overlapping time intervals)")
    
    
    def select_dates(self, start=None, stop=None, bouts=False):
        if bouts:
            return __class__.__select_dates(self.bouts, start, stop)
        else:
            return __class__.__select_dates(self.activity, start, stop)
    
    
    def __adjust_start_stop(self, start=None, stop=None):
        """Adjusts start and stop timestamps so that there is whole number of periods between them."""
        if start is None:
            start = self.__activity[0] - (self.__activity[0] - self.__t0) % self.__day
        else:
            start = pd.Timestamp(start).asm8
        if stop is None:
            stop = self.__activity[-1]
            stop = stop - (stop - start) % self.__day + self.__day
        else:
            stop = pd.Timestamp(stop).asm8
            stop = stop - (stop - start - 1) % self.__day + self.__day - 1
        self.start = start
        self.stop = stop
    
    
    def filter_inactive(self, activity_threshold=1):
        """Filters out days where activity < activity_threshold."""
        self.mask[:] = True
        for i in range(self.mask.size):
            events = __class__.__select_dates(self.__activity, 
                                            self.start + i*self.__day,
                                            self.start + (i + 1)*self.__day)
            if events.size < activity_threshold:
                self.mask[i] = False
        tmp = np.where(np.roll(np.append(self.mask, -1), 1) != np.append(self.mask, -1))[0]
        self.day_indices = tmp[0 if self.mask[0] else 1 : None if self.mask[-1] else -1].reshape(-1, 2)
        self.days = self.mask.sum()
        self.adjust_bouts(self.__max_gap, self.__min_duration, self.__min_count)
        self.activity_threshold = activity_threshold
    
    
    def activity_bouts(self, max_gap='1m', min_duration='0m', min_count=2):
        max_gap = pd.Timedelta(max_gap).asm8
        min_duration = pd.Timedelta(min_duration).asm8
        bout_starts = np.nonzero(np.diff(self.activity, 
                                         prepend=(self.activity[0] - max_gap - 1)) > max_gap)[0]
        bout_ends = np.nonzero(np.diff(self.activity, 
                                       append=(self.activity[-1] + max_gap + 1)) > max_gap)[0]
        keep_indexes = np.nonzero((bout_ends - bout_starts >= min_count) & 
                                  (self.activity[bout_ends] - self.activity[bout_starts] >= min_duration))
        indexes = np.vstack((bout_starts[keep_indexes], bout_ends[keep_indexes])).T
        return self.activity[indexes]
        
    
    def adjust_bouts(self, max_gap='1m', min_duration='0m', min_count=2):
        self.__max_gap = max_gap
        self.__min_duration = min_duration
        self.__min_count = min_count
        self.bouts = self.activity_bouts(max_gap, min_duration, min_count)
    
    
    def discretize(self, step=None, bouts=False):
        step, steps_per_day = self.__get_step_spd(step)
        if not bouts:
            intervals = np.arange(self.start, self.stop + step, step)
            result, _ = np.histogram(self.activity, intervals)
        else:
            intervals = np.arange(self.start, self.stop + step, step)
            result = np.zeros(len(intervals) - 1, dtype='d')
            for i, b in zip(count(), np.digitize(self.bouts.astype('i8'), intervals.astype('i8')) - 1):
                if b[0] < len(result):
                    result[b[0]:(b[1]+1)] += 1.0
                    result[b[0]] -= (self.bouts[i, 0] - intervals[b[0]]) / step
                if b[1] < len(result):
                    result[b[1]] -= (intervals[b[1]+1] - self.bouts[i, 1]) / step
        return (intervals[:-1][np.repeat(self.mask, steps_per_day)], 
                result[np.repeat(self.mask, steps_per_day)])
    
    
    
    
    
    def periodogram(self, step=None, min_period='16h', max_period='32h', bouts=False):
        step = self.__get_step(step)
        min_period = pd.Timedelta(min_period).asm8
        max_period = pd.Timedelta(max_period).asm8
        if min_period % step + max_period % step != self.__zero:
                raise ValueError(f"min_period and max_period should be divisible "
                                 f"by step ({pd.Timedelta(step)})")
        timestamps, values = self.discretize(step, bouts=bouts)
        # Pad zeros to not lose values at the end of data
        values = np.pad(values, (0, max_period//step - 1))
        n = values.size
        result = np.zeros(max_period//step - min_period//step + 1)
        for i, p in enumerate(np.arange(min_period//step, max_period//step + 1)):
            k = n//p
            tmp = values[:k*p].reshape((k, p))
            result[i] = k*p*tmp.mean(axis=0).var() / tmp.var()
        periods = np.arange(min_period, max_period + step, step, dtype='<m8')
        return periods, result
    
    
    def plot_periodogram(self, step=None, min_period='16h', max_period='32h', bouts=False,
                         filename=None, width=1000, height=600, dpi=96):
        periods, values = self.periodogram(step, min_period, max_period, bouts)
        graph_color = '#000000'
        if filename is not None:
            filename = Path(filename)
        fig = plt.figure(figsize=(width/dpi, height/dpi))
        n = periods.size
        offset = periods[0] % self.__hour
        if not offset:
            start = periods[0]
        else:
            start = periods[0] - offset + self.__hour
        tick_pos = np.arange(start, periods[-1] + self.__hour - offset, self.__hour)
        tick_labels = []
        for tick in tick_pos:
            tick_labels.append(str(tick//self.__hour))
        plt.xticks(ticks=tick_pos.astype('i8'), labels=tick_labels)
        plt.xlim([periods[0], periods[-1]])

        plt.plot(periods, values, color=graph_color)
        fig.text(0.5, 0.95, f"Periodogram {self.descr}", ha='center', fontsize=20, wrap=False)
        fig.text(0.5, 0.0, f"Maximal power at period "
                           f"{pd.Timedelta(periods[values.argmax()]) / self.__hour :.2f} hours",
                 ha='center', fontsize=20, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    
    def light_activity(self, bouts=False):
        result = np.zeros(self.total_days)
        total_night_activity = 0
        total_activity = 0
        mean_night_activity = 0
        if not bouts:
            for i in range(self.total_days):
                if self.mask[i]:
                    night_pos = self.night[i]
                    timestamps = self.select_dates(self.start + i*self.__day, self.start + (i + 1)*self.__day)
                    dayly_activity = timestamps.size
                    timestamps = ((timestamps - self.__t0) % self.__day).reshape(1, -1)
                    dayly_night_activity = ((timestamps >= night_pos[:, 0].reshape(-1, 1)) & 
                                            (timestamps < night_pos[:, 1].reshape(-1, 1))).max(axis=0).sum()
                    total_night_activity += dayly_night_activity
                    total_activity += dayly_activity
                    if dayly_activity:
                        result[i] = 1 - dayly_night_activity / dayly_activity
        else:
            for i in range(self.total_days):
                if self.mask[i]:
                    night_pos = np.expand_dims(self.night[i], -1)
                    timestamps = self.select_dates(self.start + i*self.__day, 
                                                   self.start + (i + 1)*self.__day, 
                                                   bouts=True)
                    timestamps = np.expand_dims((timestamps - self.__t0) % self.__day, 0)
                    dayly_night_activity = np.maximum(np.minimum(timestamps[:, :, 1], night_pos[:, 1]) - 
                                                      np.maximum(timestamps[:, :, 0], night_pos[:, 0]), 
                                                      self.__zero).sum()
                    dayly_activity = (timestamps[:, :, 1] - timestamps[:, :, 0]).sum()
                    total_night_activity += dayly_night_activity
                    total_activity += dayly_activity
                    if dayly_activity:
                        result[i] = 1 - dayly_night_activity / dayly_activity

        if total_activity:
            mean_night_activity = 1 - total_night_activity / total_activity
        return result[self.mask], mean_night_activity
    
    
    def plot_light_activity(self, bouts=False, filename=None, width=1000, height=600, dpi=96):
        values, total = self.light_activity(bouts)
        graph_color = '#000000'
        total_color = '#808080'
        max_ticks = 20
        if filename is not None:
            filename = Path(filename)
        fig = plt.figure(figsize=(width/dpi, height/dpi))
        plt.ylim(0, 1)
        tick_step = self.days // (max_ticks - 1) + 1
        tick_mask = np.full(self.days, False, dtype='bool')
        for i in range(0, self.days, tick_step):
            tick_mask[i] = True
        tick_mask[-1] = True
        tick_pos = np.arange(self.days)[tick_mask]
        tick_labels = np.arange(self.start, self.stop, self.__day)[self.mask][tick_mask].astype('datetime64[D]')
        plt.xticks(tick_pos, tick_labels, rotation=90)
        plt.plot(values, color=graph_color)
        plt.axhline(total, color=total_color)
        fig.text(0.5, 0.95, f"Light Phase Activity {self.descr}", ha='center', fontsize=20, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    
    def interdaily_stability(self, step=None, bouts=False):
        step, steps_per_day = self.__get_step_spd(step)
        timestamps, values = self.discretize(step, bouts=bouts)
        tmp = values.reshape((self.days, steps_per_day))
        result = 0.0
        var = tmp.var()
        if var and not np.isnan(var):
            result = tmp.mean(axis=0).var() / var
        return result
    
    
    def intradaily_variability(self, step=None, bouts=False):
        step, steps_per_day = self.__get_step_spd(step)
        timestamps, values = self.discretize(step, bouts=bouts)
        result = np.zeros(self.days)
        for i in range(self.days):
            tmp = values[i*steps_per_day:(i+1)*steps_per_day]
            if tmp.var():
                result[i] = (np.diff(tmp) ** 2).sum() / tmp.var() / (steps_per_day - 1)
        total = 0.0
        var = values.var()
        if var and not np.isnan(var):
            total = (np.diff(values) ** 2).sum() / var / (values.size - 1)
        return result, total
    
    def plot_intradaily_variability(self, step=None, bouts=False,
                                    filename=None, width=1000, height=600, dpi=96):
        values, total = self.intradaily_variability(step, bouts)
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
        tick_labels = np.arange(self.start, self.stop, self.__day)[self.mask][tick_mask].astype('datetime64[D]')
        plt.xticks(tick_pos, tick_labels, rotation=90)
        plt.ylim(0, max(total, values.max())*1.05)
        plt.plot(values, color=graph_color)
        plt.axhline(total, color=total_color)
        fig.text(0.5, 0.95, f"Intradaily Variability {self.descr}", ha='center', fontsize=20, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
            
    
    def relative_amplitude(self, step=None, most_active='10h', least_active='5h', bouts=False):

        def window1d(a, width, step=1):
            return a[np.arange(0, width, step)[None, :] + np.arange(0, a.size-width+1, step)[:, None]]

        step, steps_per_day = self.__get_step_spd(step)
        most_active = pd.Timedelta(most_active).asm8
        least_active = pd.Timedelta(least_active).asm8
        if most_active + least_active + min(most_active, least_active) > self.__day:
            raise ValueError(f"most_active + least_active + min(most_active, least_active) "
                             "should be no greater than 1 day")
        if most_active <= self.__zero:
            raise ValueError(f"most_active should be > 0")
        if least_active <= self.__zero:
            raise ValueError(f"least_active should be > 0")
        if most_active % step != self.__zero:
            raise ValueError(f"most_active should be divisible by step ({pd.Timedelta(step)})")
        if least_active % step != self.__zero:
            raise ValueError(f"least_active should be divisible by step ({pd.Timedelta(step)})")
        timestamps, values = self.discretize(step, bouts=bouts)
        most_active_steps = most_active // step
        least_active_steps = least_active // step
        result = np.zeros(self.days)
        total_most_active = 0
        total_least_active = 0
        for i in range(self.days):
            start = i*steps_per_day
            stop = (i+1)*steps_per_day
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
            if most_active_idx + most_active_steps + least_active_steps <= steps_per_day:
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
                if least_active_idx + least_active_steps + most_active_steps <= steps_per_day:
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
        return result, total
    
    
    def plot_relative_amplitude(self, step=None, most_active='10h', least_active='5h', bouts=False,
                                filename=None, width=1000, height=600, dpi=96):
        values, total = self.relative_amplitude(step, most_active, least_active, bouts)
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
        tick_labels = np.arange(self.start, self.stop, self.__day)[self.mask][tick_mask].astype('datetime64[D]')
        plt.xticks(tick_pos, tick_labels, rotation=90)
        plt.ylim(0, 1)
        plt.bar(np.arange(self.days), values, color=graph_color)
        plt.axhline(total, color=total_color)
        fig.text(0.5, 0.95, f"Relative Amplitude {self.descr}", ha='center', fontsize=20, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    
    def daily_bouts(self, max_gap=None, min_duration=None, min_count=None, timescale='1s'):
        if max_gap is None:
            max_gap = self.__max_gap
        if min_duration is None:
            min_duration = self.__min_duration
        if min_count is None:
            min_count = self.__min_count
        timescale = pd.Timedelta(timescale).asm8
        bout_counts = np.zeros(self.total_days, dtype='i8')
        bout_durations = np.zeros(self.total_days, dtype='float64')
        timeseries = self.activity_bouts(max_gap, min_duration, min_count)
        for i in range(self.total_days):
            if self.mask[i]:
                timestamps = __class__.__select_dates(timeseries,
                                                      start=(self.start + i*self.__day), 
                                                      stop=(self.start + (i + 1)*self.__day))
                n_bouts = len(timestamps)
                bout_counts[i] = n_bouts
                if n_bouts:
                    bout_duration = (timestamps[:, 1] - timestamps[:, 0]).sum()/timescale
                    bout_durations[i] = bout_duration / n_bouts # Mean bout duration
        return bout_counts[self.mask], bout_durations[self.mask]
    
    
    def plot_daily_bouts(self, max_gap=None, min_duration=None, min_count=None, timescale='1s',
                         filename=None, width=1000, height=600, dpi=96):
        bout_counts, bout_durations = self.daily_bouts(max_gap, min_duration, min_count, timescale)
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
        tick_labels = np.arange(self.start, self.stop, self.__day)[self.mask][tick_mask].astype('datetime64[D]')
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
    
    
    def plot_bout_histogram(self, max_gap=None, min_duration=None, min_count=None, timescale='1s', bins=20,
                            filename=None, width=1000, height=600, dpi=96):
        timescale = pd.Timedelta(timescale).asm8
        if max_gap is None:
            max_gap = self.__max_gap
        if min_duration is None:
            min_duration = self.__min_duration
        if min_count is None:
            min_count = self.__min_count
        timeseries = self.activity_bouts(max_gap, min_duration, min_count)
        values = (timeseries[:, 1] - timeseries[:, 0]) / timescale
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
    
    
    def activity_onset(self, step=None, percentile=20, N='6h', M='6h', bouts=False):
        step, steps_per_day = self.__get_step_spd(step)
        timestamps, values = self.discretize(step, bouts=bouts)
        N = pd.Timedelta(N).asm8 // step
        M = pd.Timedelta(M).asm8 // step
        conv = np.array([-1]*N + [1]*M)
        result = np.zeros(self.days, dtype='<M8[ns]')
        for i in range(self.days):
            tmp = values[i*steps_per_day:(i+1)*steps_per_day]
            active = tmp >= np.percentile(tmp[tmp != 0], percentile, interpolation='higher')
            tmp[:] = -1
            tmp[active] = 1
            idx = np.correlate(conv, tmp, mode='same').argmax()
            result[i] = timestamps[i*steps_per_day + idx]
        return result
    
    
    def plot_activity_onset(self, step=None, percentile=20, N='6h', M='6h', bouts=False,
                            filename=None, width=1000, height=600, dpi=96):
        values = self.activity_onset(step, percentile, N, M, bouts)
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
        tick_labels = np.arange(self.start, self.stop, self.__day)[self.mask][tick_mask].astype('datetime64[D]')
        plt.xticks(tick_pos, tick_labels, rotation=90)
        plt.plot(values)
        fig.text(0.5, 0.95, f"Activity Onset {self.descr}", ha='center', fontsize=20, wrap=False)
        if filename:
            plt.close(fig)
            fig.savefig(filename, dpi=dpi)
            print(f"File succesfully saved to {filename}")
        else:
            plt.show()
    
    def plot_actogram(self, step=None, bouts=True, filename=None, width=1000, height=100, dpi=96):
        if filename is not None:
            filename = Path(filename)
        step, steps_per_day = self.__get_step_spd(step)
        bar_color = '#000000'
        timestamps, values = self.discretize(step, bouts=bouts)
        fig, subplots = plt.subplots(self.days, 2, sharex=True, sharey=True,
                                     figsize=(width/dpi, height*self.days/dpi), dpi=dpi,
                                     gridspec_kw={'hspace': 0, 'wspace': 0})
        minute_offset = (self.start - self.__t0) % self.__hour
        tick_start = minute_offset / self.__day
        hours_per_tick = 2
        tick_pos = np.arange(tick_start, 0.999, hours_per_tick/24)*steps_per_day
        tick_labels = []
        if not minute_offset:
            first_tick = self.start
        else:
            first_tick = self.start - minute_offset + self.__hour
        for i in range(len(tick_pos)):
            tick_label = pd.Timestamp(first_tick + i*hours_per_tick*self.__hour).strftime('%H')
            tick_labels.append(tick_label)
        hour_offset = ((self.start - self.__t0) % self.__day) / self.__day
        fig.subplots_adjust(top=1-0.5/(self.days+1))
        fig.text(0.5, 1 - 0.25/(self.days + 1), f"Actogram {self.descr}", ha='center', fontsize=20, wrap=False)
        night = [self.night[i] for i in range(self.total_days) if self.mask[i]]
        for i in range(1, 2*self.days):
            d = i // 2
            night_pos = (night[d] / self.__day - hour_offset) * steps_per_day
            if d+1 < self.days:
                night_pos2 = (night[d+1] / self.__day - hour_offset + 1) * steps_per_day
            else:
                night_pos2 = []
            ax = subplots[d - (i+1)%2, (i+1) % 2]
            ax.bar(np.arange(steps_per_day), values[d*steps_per_day : (d+1)*steps_per_day], 
                   width=1, align='edge', color=bar_color)
            for j in range(0, len(night_pos)):
                ax.axvspan(night_pos[j, 0], night_pos[j, 1], facecolor='#808080', alpha=0.5)
            for j in range(0, len(night_pos2)):
                ax.axvspan(night_pos2[j, 0], night_pos2[j, 1], facecolor='#808080', alpha=0.5)
            if not i%2:
                ax.yaxis.set_label_position('right')
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