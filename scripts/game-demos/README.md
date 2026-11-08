# Games page demo media

All published demos are animated WebP images. Do not add MP4 files or video
players: articles, home cards, archives, and Games share native image delivery.
The existing GIF articles remain supported. Animated WebP avoids GIF's indexed
palette; lossy WebP compression is used without palette reduction.

Sources in sibling repositories:

- rabbitrun: recorded with the built-in `--record-demo` command
- succubus-live: recorded from the published browser game in Japanese
- gozen: `gozen/docs/images/go-zen.gif`

Output: `content/games/media/{name}-demo.webp`.

```sh
ffmpeg -i "$source" -an -vf fps=15 -c:v libwebp_anim -quality 85 \
  -compression_level 4 -loop 0 "$animation"
```

Long animations must fit Hugo's 384 MiB per-image frame-buffer limit.
The migrated sources use 8 fps at 720 px width for Death March work,
8 fps at 640 px for Succubus Live, 10 fps for Rabbit Run and kube-prompt,
and 15 fps for the phone demos and Gozen. Timing and looping are retained;
no indexed-color palette is introduced.

Keep temporary recordings outside the content tree. Hugo's existing image
pipeline creates responsive animated WebP derivatives with native lazy loading.
`check_asset_delivery.py` rejects published MP4 files and video elements;
`check_home_media_browser.mjs` checks that card images actually animate.

Rabbit Run was re-recorded with its built-in automatic demo: 60 seconds each of
`cool`, `cute`, `gyal`, and `street`, plus 25 seconds of `gyal` on stage 4.
The edit uses seconds 14–20 in the order `gyal`, `cool`, `cute`, `street`,
then seconds 8–14 of stage 4: exactly 30 seconds in total.
The secret bunny is excluded.

Succubus Live uses a 1280×720 browser viewport, Japanese language, a viewer named
ゲスト, and the game's fullscreen view. The video combines the lobby and six solo
streams. The introduction image is a fullscreen Mora/Pim collaboration screenshot.
Only in the recording browser, the collaboration was unlocked and its selection
chance fixed to show that existing episode; no script or artwork was generated.
The game repositories and published game were not changed.

Games' Open Graph image is Ox's Shield Rush cut-in, rendered directly at
1920×1080 with the `battle` run in Gozen's `docs/images/manifest.yaml` (seed 7,
`capture-go-zen-battle.txt`). `fight_b154.png` is encoded as WebP quality 88,
without resizing or the GIF's palette reduction.

The Rabbit Run edit uses `trim` + `setpts=PTS-STARTPTS` on each input before
concatenation, so keyframe seeking cannot add repeated or overlapping segments.
Hugo image derivatives have content-hashed URLs to avoid stale browser caches.
