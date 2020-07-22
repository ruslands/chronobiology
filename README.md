class DBQuery():

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


class CycleAnalyzer():

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