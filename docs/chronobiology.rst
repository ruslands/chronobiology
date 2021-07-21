Chronobiology module documentation
==================================

Main module providing classes and methods to collect, generate, calculate and plot
circadian cycles data.

.. automodule:: chronobiology.chronobiology
    :members: generate_data, generate_night

    .. rubric:: Classes

    .. autosummary::
        :nosignatures:

        DBQuery
        CycleAnalyzer

    .. rubric:: Methods

    .. autosummary::
        :nosignatures:

        generate_data
        generate_night

    .. autoclass:: chronobiology.chronobiology.DBQuery
        :members:

        .. rubric:: Methods

        .. autosummary::
            :nosignatures:

            get_measurements
            get_tags
            get_fields
            get_keys
            get_data

    .. autoclass:: CycleAnalyzer
        :members:

        .. rubric:: Properties

        .. autosummary::
            timestamps
            activity
            night
            bouts

        .. rubric:: Methods

        .. autosummary::
            :nosignatures:

            activity_bouts
            update_bouts
            filter_inactive
            plot_actogram
            periodogram
            plot_periodogram
            light_activity
            plot_light_activity
            interdaily_stability
            intradaily_variability
            plot_intradaily_variability
            relative_amplitude
            plot_relative_amplitude
            daily_bouts
            plot_daily_bouts
            plot_bout_histogram
            activity_onset
            plot_activity_onset

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
