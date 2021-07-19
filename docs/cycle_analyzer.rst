CycleAnalyzer documentation
===========================

.. autoclass:: chronobiology.chronobiology.CycleAnalyzer
    :members:

    .. note::
        Most methods can base their analysis on either number of activity events or
        precalculated activity bouts.

    .. note::
        Methods accepting timespan parameters (e.g. ``start``, ``min_duration`` and all
        other parameters of type ``str|int|timedelta``) can treet them differently
        depending on their type:

            ``str`` parameters are parsed like timedelta strings (e.g. ``'03:43:40'``),

            ``int`` parameters are treated as the number of nanoseconds,

            ``timedelta`` parameters are treated as they are.
