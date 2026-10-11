# Project architecture diagrams

| Diagram | Editable vector | Image preview |
| --- | --- | --- |
| Sources, merge, split and representations | [SVG](01_data_preprocessing.svg) | [PNG](01_data_preprocessing.png) |
| DAE, supervised models and evaluation | [SVG](02_models_training.svg) | [PNG](02_models_training.png) |
| Current beta and proposed inference | [SVG](03_application.svg) | [PNG](03_application.png) |

These diagrams show model names and the flow of data to outputs, without model
parameter details. Green stages are implemented; grey stages are proposed. Yield prediction models
remain untrained. DAE reconstruction error is not supervised yield accuracy.

See also the [detailed raw field selection and merge](../figures/Raw_Data_Feature_Selection_and_Merge.svg).

To regenerate from the project root:

    python docs/source/build_architecture_diagrams.py

The generated SVGs contain editable text and vector shapes. PNGs are convenient
for GitHub preview and presentations.
