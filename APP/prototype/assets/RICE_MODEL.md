# Rice 3D model

Original procedural geometry in `rice-scene.js`, rendered with locally bundled
Three.js r170 (MIT; see THREE-LICENSE.txt). No external plant model or photographic
billboard is used. A generated epidermis albedo/bump texture is mapped onto
the real curved meshes. Curved leaf ribbons have folds, tapered tips, UV coordinates,
normals and midribs. Culms, nodes, rachises, branches and grains are 3D meshes.

The camera approaches the selected blade along its transformed surface normal.
Dragging then orbits that position in three dimensions. Scroll changes the
attached target leaf or panicle, not the plant asset. Procedural UV shaders show
illustrative symptoms; severity is not calibrated biological progression.
All leaves, stems and grain heads remain opaque. A ray-tested camera approach
looks for a clearer view of the selected surface without fading the plant.

The default symptom comparison distributes different illustrative conditions
across the leaves, with per-leaf seed variation. It is explicitly a teaching
comparison, not a biological claim that one plant has all conditions. Uncheck
the comparison for a single-condition example, or select Normal rice for a
healthy plant. View all leaves returns to the whole specimen; clicking a blade
focuses its assigned example. Panicle blight stays on grain heads; the central
dry-shoot example represents dead heart, not a spreading foliar lesion pattern.

Wind uses culm-root and leaf-base transforms; its strength responds to pointer
velocity. Offscreen/hidden scenes pause and reduced-motion mode is supported.

`rice-plant.model.json` is a portable Three.js ObjectLoader-compatible geometry
snapshot, exported by `node APP/tests/test_rice_model.mjs --export`.
The live scene uses the same builder, with custom symptom shaders and camera
controls added at runtime. The JSON snapshot alone does not include those
JavaScript behaviours. Earlier raster studies remain archived source artwork,
not active scene inputs. No ML model, training sample or prediction is changed.

The leaf albedo was generated with the built-in image tool. Prompt: fill the
entire portrait rectangle with extreme-macro rice-leaf epidermis, fine parallel
vertical veins, subtle waxy microtexture and natural olive-green variation;
uniform diffuse lighting; no leaf outline, plant silhouette, lesions, background,
text, highlights or shadows. It is illustrative material, not a field observation.
Saved as `rice-leaf-albedo.png`. The same map supplies subtle bump detail.
Grains use pointed lathed husks, varied proportions and orientations, UV husk
grooves, and individual ripeness colours. Four branched heads contain 672 grains.
