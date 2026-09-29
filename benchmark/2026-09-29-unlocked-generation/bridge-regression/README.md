# Independent bridge regression experiment

The 846/22df single-file A/B isolates the regression to the bridge. Restoring
the window cohort and removing manifest JNI did not recover ZigZag. The
responsible function is unresolved. Dynamic sections and import/export set
differences are recorded here; absence/presence of a symbol alone is not a
causal explanation. The full canonical real-work bridge failed the existing
FN03 marker check and was not deployed. Its source is not equivalent to the
accepted 846 stage-ack build. Further source-group bisection belongs to a
separate task; the authorized v3a combination remains resident.
