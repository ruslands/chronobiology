from datetime import datetime
from itertools import count
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from influxdb import InfluxDBClient
import numpy as np
import pandas as pd


class DBQuery():
    """Class to access InfluxDB 1.x and select records from it."""

    def __init__(
        self,
        database: str,
        username: str,
        password: str,
        host: str = 'localhost',
        port: int = 8086,
    ) -> None:
        """
        :type database: str
        :param database: Name of the database.

        :type username: str
        :param username: Name of user.

        :type password: str
        :param password: User password.

        :type host: str, optional
        :param host: IP adress, defaults to ``localhost``.

        :type port: int, optional
        :param port: Connection port, defaults to ``8086``.
        """
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


    def get_measurements(self) -> List[str]:
        """Get list of all measurments (series) in the database.

        :rtype: list[str]
        :return: List of all measurement names in the database.
        """
        query = f"SHOW MEASUREMENTS;"
        result = self.client.query(query).raw['series']
        if result:
            return [x[0] for x in result[0]['values']]
        else:
            return []


    def get_tags(self, series: str) -> List[str]:
        """Get all tags (tag names) in a series.

        :type series: str
        :param series: Name of the series.

        :rtype: list[str]
        :return: List of all tag names in the series.

        .. note::
            Returns an empty list if the query does not return any vaues, for example,
            if there are no tags in the series or if there is no series with the
            given name.
        """
        query = f'SHOW TAG KEYS FROM "{series}";'
        result = self.client.query(query).raw['series']
        if result:
            return [x[0] for x in result[0]['values']]
        else:
            return []


    def get_fields(
        self, series: str, return_types: bool = False
    ) -> Union[List[str], Tuple[List[str], List[str]]]:
        """Get all fields in a series.

        :type series: str
        :param series: Name of the series.

        :type return_types: bool, optional
        :param return_types: Indicates if field types should be returned, defaults to
            ``False``.

        :rtype: list[str]|(list[str], list[str])
        :return:
            If ``return_type == False``
                List of field names.

            If ``return_type == True``
                Field names and the corresponding InfluxDB field types as a pair of
                lists of strings.
                The possible types are: ``integer``, ``float``, ``string`` and
                ``boolean``.

        .. note::
            Returns an empty list if the query does not return any vaues, for example,
            if there are no tags in the series or if there is no series with the
            given name.
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


    def get_keys(self, series: str, tag: str) -> List[str]:
        """Get list of all tag values for a given tag in a series.

        :type series: str
        :param series: Name of the series.

        :type tag: str
        :param tag: Name of the tag.

        :rtype: list[str]
        :return: List of all values of the tag in the series.

        .. note::
            Returns an empty list if the query does not return any vaues, for example,
            if there are no tags in the series or if there is no series with the
            given name.
        """
        query = f'SHOW TAG VALUES FROM "{series}" WITH KEY = "{str(tag)}";'
        result = self.client.query(query).raw['series']
        if result:
            return [x[1] for x in result[0]['values']]
        else:
            return []


    def get_data(
        self,
        series: str,
        fields: Union[str, Sequence[str], Dict[str, Union[str, type]]],
        keys: Optional[Dict[str, Any]] = None,
        start: Optional[Union[str, int, datetime]] = None,
        stop: Optional[Union[str, int, datetime]] = None,
        local_tz: bool = False,
    ) -> Dict[str, np.ndarray]:
        """Get data (records) for specified fields/tags in a series.

        :type series: str
        :param series: Name of the series.

        :type fields: str|list[str]|tuple[str]|set[str]|dict[str: str|type]
        :param fields: Name(s) of fields/tags in the series.
            This parameter is treated differently depending on it's type:

            ``str``
                Treated as a single field/tag name to return.
                If ``fields`` = ``'*'`` then all fields and tags are returned.

            ``list[str]``, ``tuple[str]`` or ``set[str]``
                Treated as a collection of field/tag names to return.

            ``dict[str: str|type]``
                The keys are treated as field/tag names, and the values are treated as
                numpy types (or names of numpy types) of the corresponding keys.

                The output is converted from InfluxDB types to the types
                specified in the dictionary.

                Use ``None`` as a field type to enable type autodetection and/or
                avoid type conversion for that field.

        :type keys: None|dict[str: obj], optional
        :param keys: Dictionary providing rules to select records with specific
            field/tag values, defaults to ``None``.

            If ``None`` then selected records are not filtered.
            Otherwise the dictionary is treated as follows:

            Key
                Name of the filtered field/tag.

            Values
                Value(s) of the corresponding field/tag to be selected.

                Each value can be a scalar or a collection of all values to be selected
                (``list``, ``tuple`` or ``set``)

        :type start: None|str|int|datetime, optional
        :param start: Inclusive lower time boundary for the returned data, defaults to
            ``None``.

            ``None`` indicates no lower boundary.

            ``str`` is interpreted as a timestring.

            ``int`` is interpreted as a Unix timestamp.

            ``datetime`` is used as is.

        :type stop: None|str|int|datetime, optional
        :param stop: Exclusive upper time boundary for the returned data, defaults to
            ``None``.

            ``None`` indicates no upper boundary.

            ``str`` is interpreted as a timestring.

            ``int`` is interpreted as a Unix timestamp.

            ``datetime`` is used as is.

        :type local_tz: bool, optional
        :param local_tz: Indicates whether local or UTC time is used in the code,
            defaults to ``False`` (UTC).


        :rtype: dict[str: np.array]
        :return: Dictionary constructed as follows:

            Key
                Field/tag name.

            Value
                Numpy array of the corresponding field/tag values.
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


