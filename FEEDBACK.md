# Jarvis-Amds — User Feedback (verbatim review, 2026-10-31)

> The Background and Colors are good with contrast and easy on the Human eye.
> Glass morphism is also Good.

> The video couldn't use the generated image files perfectly.
> (there is a lot of space left below the top portion of the video)

> The Video only contains text and one Icon in a frame.
> We should be able to explain using pictures, Diagrams and Icons.

> The Captions and audio speed are very fast for Humans.

> The Captions should show one word only once.

> LLM should be able to understand the screen geometry for a 9:16 video
> and render the Diagrams, Icons and Pictures.

> It should leave a 7-12% free space buffer on left and top and 10-15% on
> right and bottom as shorts, tik tok and insta takes out that space for their apps.

> The Generated Images can be like fillers between the content.

> LLM should also act as a judge and check the frames before passing for
> stitching the video.

## Translation to build tasks
1. KineticScene: add an image/diagram slot between headline and body;
   render the explainer stills (or generated diagrams) inside the card to fill space.
2. Storyboard prompt: pass the 9:16 canvas + safe-area rects to the LLM so it
   composes multi-element frames (picture + icon + text), not text-only.
3. TTS: lower the speech rate (e.g. edge-tts rate -20/-25%) and slow the caption
   display cadence accordingly.
4. TopCaptions: window size = 1 (single word).
5. All layout math respects: left/top 7–12% buffer, right/bottom 10–15% buffer.
6. New QA stage in the engine: after rasterization, sample frames, run an LLM
   judge (vision), gate stitching on pass; log failures per scene.
