# Encoder acquisition decision required

Status: unresolved. Frozen v36 remains unqualified. No implementation or gate change is authorized by this document.

## Retained observation

The actual native Stage5 battery failed `noise_is_colored` for `pulse_speed` and `pulse_position`: median residual correlation time10seconds, equal to the10second scan. The unchanged check rejects every included instrument class whose median is no greater than the scan. Other error-level checks, including PCA25components across41tags, passed. See `work/press-stage5-v36.log` and the acquisition epoch record.

The declared pulse acquisition has zero lag, zero stochastic noise and deterministic16bit quantization. Measured-minus-true residual therefore contains rounding error. Rounding error need not be time-correlated. Two independent source reviews confirmed that this is a measurement-design/gate incompatibility, not evidence that shaft motion is incorrect. White rounding error must not be relabelled as an analog instrument defect.

## Evidence needed for a revised acquisition design

The intended encoder, speed sensor and PLC/readback model numbers, configuration and acquisition topology are needed to establish any actual averaging, filtering, oscillator or thermal response. The implementation must distinguish fast controller feedback from any slower historian/readback path. Any revised gain, latency or timing behavior must affect the appropriate actual signal chain and preserve counter, event, control and engineering checks.

Manufacturer documentation establishes possible mechanisms, not this press's parameters:

- [Beckhoff frequency/velocity measurement](https://infosys.beckhoff.com/content/1033/ej5021/13501598347.html) documents a frequency measurement window and IIR filter. It does not establish the intended press's settings or justify a filter longer than10seconds.
- [HEIDENHAIN linear encoder documentation](https://www.heidenhain.de/fileadmin/pdf/en/01_Products/Prospekte/PR_Linear_Encoders_for_Numerically_Controlled_Machine_Tools_ID571470_en.pdf) describes model-dependent thermal behavior and signal-processing-dependent position noise. It does not identify the intended press's transducer or a numerical stochastic process for it.
- [Renishaw scale mounting and thermal performance](https://www.renishaw.com/en/white-paper-mounting-encoder-scales-for-optimum-thermal-performance--44316) explains temperature-induced scale length changes. A linear scale's behavior cannot automatically be assigned to a rotary shaft encoder or a speed timebase.

These sources are grounds for investigation, not calibration evidence. No hardware selection, procurement recommendation or physical accuracy claim follows from them.

## Boundary

Do not add an arbitrary colored process, lengthen a filter to fit the failed statistic, change the class to bypass the test, or silently exempt digital tags. A documented synthetic acquisition design may be proposed explicitly if hardware is not selected, but its physical basis, parameters and limitations must be reviewed before implementation. Until then the unchanged native gate remains failed, and the513case matrix and six full90day press qualification runs remain held.
