# T11 performance baseline

## Static audit before the Canvas change

The Web game table had no travel animation for Slash or Dodge. Target selection used a full-board SVG with animated stroke dashes and a Gaussian blur filter. Its endpoints were fixed viewBox coordinates, so they did not track actual player portraits when the board layout changed. The active-player glow and damage/heal portrait feedback animated box-shadow and filter, which require repeated paint work.

The existing 100 ms decision timer updates only the timer component. No React state loop was driving combat particles because combat particles did not yet exist.

## Measurement status

The original baseline was not recorded with a browser frame trace before changes. FPS, average frame time, worst spike and long-task counts are **unmeasured**; no numeric claim is made. Browser profiling should use idle, card hover/select, target selection, beam, Slash, Dodge, damage, chain, and simultaneous FX at 1366×768, 1600×900 and 1920×1080.

## T11 implementation notes

The new Canvas runtime has one requestAnimationFrame loop for active effects and beams, capped effect count, cached portrait anchors, ResizeObserver updates, capped device pixel ratio by quality setting, hidden-tab pause, reduced-motion timing, and teardown. React only sends target IDs and semantic game events. Low quality removes beam motes and Dodge echoes.

The current implementation is a lightweight 2D foundation. Quantitative performance validation, particle/texture pooling, and a complete god portrait runtime remain open.
