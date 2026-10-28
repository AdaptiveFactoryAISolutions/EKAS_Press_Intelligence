# Sensor value

`sensor_gaps` adds each unavailable public candidate signal and recomputes the complete discrimination assessment. Gain is the difference in separated pair counts, with the denominator and exact newly separated classes retained. Zero-gain single additions are omitted. Conjunctive sets may need several additions before showing a gain; this implementation does not search multi-sensor bundles.

Gains are conditional on the supplied instrumentation. Never sum two candidate gains: call the function again after selecting a signal. Recommendations sort by the public source/installation priority, then descending pair gain. Existing control signals precede PLC data, added discrete inputs and analog sensors. Metadata exposes source availability, input possibility, analog/discrete kind and hardware requirements. Costs are not quoted or inferred.

`plc_input_possible=true` identifies an existing synthetic control channel suitable for mapping investigation, not a qualified installed plant input. For new hardware it is `null` (unknown): analog/discrete type alone does not prove controller compatibility or spare I/O capacity. Engineering must confirm the interface; `hardware_required` remains a separate field.
