\# Chest X-ray Validator



Binary semantic input validator for LungXrayAI v1.5.



\## Classes



\- NOT\_CHEST\_XRAY

\- CHEST\_XRAY



\## Input



\- RGB

\- 224 x 224 x 3

\- float32

\- pixel range before model: 0..255



Normalization is embedded inside the model.



\## Positive class



CHEST\_XRAY includes chest radiographs regardless of disease class.



\## Negative class



NOT\_CHEST\_XRAY should include diverse non-chest images,

including non-medical images and medical images from other modalities

or body regions.



\## Important



Dataset files are not committed to Git.



Avoid image leakage between train, validation, and test splits.

