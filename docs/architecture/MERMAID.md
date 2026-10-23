# Detailed architecture sources

Two editable Mermaid flowcharts describe the version 0.7.0 implementation:

- `yield-cnn-lstm.mmd`: raw sources, measured target, weather calendars/cutoff,
  time-bin features, train-only scaling, splits and model selection, scenario
  construction, every neural stage and tensor shape, LSTM gate equations,
  output arithmetic, sensitivity calculation and scope of evaluation.
- `image-efficientnet.mmd`: duplicate-safe image data, training, preprocessing,
  all EfficientNet stage dimensions, MBConv internals, logits/softmax/class order,
  uncertainty guard, actual-run stage inspection, limitations and local export.

The matching `.svg` files are already rendered and zoomable. Both source files
were parsed and rendered successfully with Mermaid before delivery.

Paste an entire `.mmd` file into a Mermaid-compatible editor, or place its
contents inside a `mermaid` fenced code block in Markdown. Export as SVG for a
large, zoomable diagram. The sources set black/white styling and Arial.

The app architecture is a separate interactive visualization: run a prediction,
then click stages to inspect actual inputs, outputs and intermediate tensors.
The source flowcharts document the computation and do not embed an example
patient/farm photo or invent example predictions. B is batch size (1 in app),
T is the valid number of ten-day weather bins, and square brackets show tensor
dimensions. The last 60 days of the proxy season do not enter the yield model.
