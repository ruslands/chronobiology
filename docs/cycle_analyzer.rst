CycleAnalyzer documentation
===========================

.. autoclass:: chronobiology.chronobiology.CycleAnalyzer
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
    
    .. _My target:
    .. note::
        Methods accepting timespan parameters (e.g. ``start``, ``min_duration`` and all
        other parameters of type ``str|int|timedelta``) can treet them differently
        depending on their type:

            ``str`` parameters are parsed like timedelta strings (e.g. ``'03:43:40'``),
        
            ``int`` parameters are treated as the number of nanoseconds,
            
            ``timedelta`` parameters are treated as they are.
