Analyzing data
==============

Class :class:`~chronobiology.chronobiology.CycleAnalyzer` is used for calculating and
plotting circadian cycles data.

Actogram
--------

The most obvious way of assessing circadian disruption is to simply look at experimental
actograms. This visual inspection should always take the form of circadian disruption into account,
and whether this is environmental or genetic in origin. This will also determine the appropriate
controls, be they baseline conditions or wildtype littermates, respectively. Furthermore, when studying
circadian disruption under different lighting paradigms, comparing activity relative to the external LD
cycle is critical. This initial visual inspection of actogram data will guide the choice of which additional
measurements are likely to be most informative.

Periodogram
-----------

The power of a periodogram provides a measure of the strength and regularity of the underlying
rhythm, with higher values indicating robust rhythms. In circadian disruption -- where rhythms are
typically less robust -- periodogram power is expected to be reduced and low values may indicate the
absence of a significant circadian rhythm. The power of the chi-square periodogram (:math:`Q_p`) has been
widely used as a measure of the robustness of circadian rhythms, and can be traced back to studies
on the effects of constant light on the strength of activity and sleep rhythms in rats. Analysis of
:math:`Q_p` based upon simulated and empirical data sets has shown that this provides a valuable measure of
the robustness of circadian rhythms. Periodogram analysis is particularly informative in internal
desynchrony, where the power of multiple periodicities within a dataset will be evident.

Activity Onset
--------------

A hallmark of normal circadian function is that activity onset is consistent from day to day.
In most records, the onset of activity is typically a more precise phase marker than the
offset of activity. As such, the variability in activity onset across multiple days -- either relative to
the light/dark cycle (phase angle of entrainment) or under constant conditions -- provides a useful
metric to describe the precision of circadian rhythms. Phase angle of entrainment and the variability
in activity onset have been widely used in the study of circadian entrainment. Activity onset
is particularly informative when studying circadian misalignment and chronodisruption, where the
phasing of activity with regard to environmental zeitgebers is expected to differ.

Light phase activity
--------------------

In nocturnal species, such as laboratory mice, activity is normally confined to the dark phase of
the light/dark cycle. A hallmark of disrupted rhythms is therefore an increased activity in the
normally inactive light phase, and such changes are expected to occur in both circadian misalignment
and chronodisruption. In diurnal species, dark phase activity can similarly be used to quantify the
amount of activity occurring in the normal inactive phase. Light phase activity has been widely used
to study defects in circadian entrainment to light as well as in disease-relevant models.
Light phase activity also provides an ideal measure to assess the
impact of misaligned feeding, a specific example of circadian misalignment.

Activity bouts
--------------

As a result of less consolidated activity and rest phases, circadian disruption is associated with an
increased number and reduced duration of activity bouts. The number and duration of activity bouts
are frequently used as a measure of fragmentation in circadian disruption. Due to the inappropriate
phasing of activity/rest cycles with regard to the external environmental, circadian misalignment,
internal desynchrony and chronodisruption are all expected to affect activity bouts.

Inter-daily stability
---------------------

Inter-daily stability (IS) measures the day-to-day reproducibility of rest/activity cycles. Patterns
of activity are typically reproducible in healthy individuals, whereas circadian disruption results in
more variable rhythms. IS was first described in the study of elderly human patients with Alzheimer’s
disease. It has subsequently been widely used in a number of human studies, and has
also been adopted for studying circadian disruption in animal models. Due to the day-to-day changes
in the relationship between circadian and environmental time, decreased IS may be expected in internal
desynchrony. However, circadian misalignment and chronodisruption may not influence IS if a stable
new phase-relationship is established.

Intra-Daily variability
-----------------------

Intra-daily variability (IV) is a measure of the fragmentation of activity rhythms. First introduced
for the study of patients with Alzheimer’s disease, like IS it has been readily adopted for the
study of animal models of circadian disruption. IV measures the frequency of transitions between
activity and rest across the day. More transitions between activity and rest result in higher IV scores.
As with activity bouts, circadian misalignment, internal desynchrony and chronodisruption may
all increase IV due to the inappropriate phasing of activity/rest cycles with regard to the external
environment. A good example of this occurs in aging, where IV increases steadily with age in mice.

Relative amplitude
------------------

Perhaps the most obvious measure of the strength of any biological rhythm is its amplitude.
A simple metric that has been widely used in human studies is relative amplitude (RA), again
originating from studies in patients with Alzheimer’s disease. RA is a simple measure of
the difference between periods of peak activity and rest. As healthy rhythms are assumed to display
consolidated activity and rest periods, RA is expected to be reduced when normal circadian rhythms
are disrupted. Both circadian misalignment and chronodisruption will reduce RA, with internal
desynchrony potentially resulting in RA values that fluctuate as periods move in and out of phase.

.. toctree::
    demos/cycle_analyzer
