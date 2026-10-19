# Archived rice illustration assets

## Leaf and condition illustrations

The superseded 2.5D scene used `rice-specimen-clean.png`, cleaned with the built-in tool
using the prompt: remove every blurred green/yellow background pixel and halo,
including spaces between stems and leaves; preserve exactly the original plant
geometry and photographic textures; genuine alpha, no new objects or backdrop.
Older detached leaf textures are retained as source artwork but no longer used
by the interactive scene. These raster specimens and detached symptom textures
are excluded from the current installer. The active scene uses true Three.js
geometry; see RICE_MODEL.md. Real photo references are documented separately in
PHOTO_CREDITS.md and are never generated artwork.

The transparent healthy leaf and nine condition textures were also generated
using the built-in image tool, editing the same healthy reference for consistent
framing. Shared brief: photographic rice tissue, fine parallel veins, natural
lighting, transparent background, no text, no icons, no background. Preserve
the reference silhouette and change only the specified visible tissue symptoms.
Variants request spindle lesions (blast), yellow/dry leaf margins (blight),
oval brown spots, narrow interveinal streaks, scraped/mined tissue (hispa),
pale yellow-green foliage (dataset downy-mildew class), dried central tiller,
yellow-orange foliage (tungro) and discoloured grain heads (panicle blight).

These are educational, photographic-style illustrations, not actual field
photographs, measured progression, training samples, or diagnostic evidence.
The progression slider reveals the edited texture; its percentage has no
biological or model-confidence meaning. Mouse velocity supplies a damped canvas
gust; this is a layered 2.5D animation with bounded turning, not a 360° mesh.

`rice-specimen-cutout.png` is generated illustrative artwork, not an observed
crop, dataset image, disease example or classifier attribution. The UI labels it
as generated. Real disease references and their licenses remain in PHOTO_CREDITS.md.

Generated using the built-in image-generation tool, then background-extraction
editing with the same tool. No external API key or additional runtime service.
The final image is bundled offline; canvas animation does not call a model.

Generation prompt:

> Use case: photorealistic-natural. Asset type: premium crop-health website botanical specimen, transparent cutout. Create a scientifically plausible photographic-style mature rice tiller, Oryza sativa, with three slender irregular green culms, long narrow arching ribbon leaves with parallel veins, and naturally drooping branched panicles bearing many tiny green-golden rice grains. Actual rice appearance, NOT maize, wheat, fern or stylized tree. Asymmetric organic branching, subtle translucency and realistic leaf surface and grain details, natural studio side light, restrained olive green/gold palette intended to sit on pure black. Portrait composition, entire visible above-ground plant contained within image with generous transparent margins at every edge; no pot, no ground, no human, no text, no background, no graphic symbols, no circles, no diagrams. Photographic realism, not flat vector or glossy plastic 3D. This is an illustrative website hero, not disease training data.

Extraction prompt:

> Edit target: this rice image. Background extraction only. Preserve exactly the photographic rice plant, all culms, every long leaf and drooping grain panicle. Remove ALL blurred green/yellow background completely and replace with genuine alpha transparency, including spaces between leaves and between grain branches. No colored glow, no black rectangle, no new background. Keep naturally detailed rice texture, no illustration simplification, no added text.
