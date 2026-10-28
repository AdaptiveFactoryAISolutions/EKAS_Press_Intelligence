# Sensor value

`sensor_gaps` adds each unavailable public candidate signal and recomputes the complete discrimination assessment. Gain is the difference in separated pair counts, with the denominator and exact newly separated classes retained. Zero-gain single additions are omitted. Conjunctive sets may need several additions before showing a gain; this implementation does not search multi-sensor bundles.

Gains are conditional on the supplied instrumentation. Never sum two candidate gains: call the function again after selecting a signal. Recommendations sort by the public source/installation priority, then descending pair gain. Existing control signals precede PLC data, added discrete inputs and analog sensors. Metadata exposes source availability, input possibility, analog/discrete kind and hardware requirements. Costs are not quoted or inferred.
