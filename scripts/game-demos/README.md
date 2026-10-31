# Games page demo media

Existing demo GIFs converted to muted H.264 MP4 (CRF 25, slow preset,
yuv420p, faststart, metadata stripped). Odd dimensions are padded to even
pixels for H.264 compatibility. Posters are the first frame encoded as WebP.

Sources in sibling repositories:

- rabbitrun: newly recorded with the built-in `--record-demo` command
- succubus-live: newly recorded from the published browser game in Japanese
- gozen: `gozen/docs/images/go-zen.gif`

Output: `content/games/media/{name}.mp4` and `{name}-poster.webp`.

```sh
ffmpeg -i "$source" -vf 'pad=ceil(iw/2)*2:ceil(ih/2)*2' -an \
  -c:v libx264 -preset slow -crf 25 -pix_fmt yuv420p \
  -movflags +faststart -map_metadata -1 "$video"
ffmpeg -i "$source" -frames:v 1 -quality 82 -map_metadata -1 "$poster"
```

Rabbit Run was re-recorded with its built-in automatic demo: 60 seconds each of
`cool`, `cute`, `gyal`, and `street`, plus 25 seconds of `gyal` on stage 4.
The edit uses seconds 14–20 in the order `gyal`, `cool`, `cute`, `street`,
then seconds 8–14 of stage 4: exactly 30 seconds in total.
The secret bunny is excluded. Example recording:

```sh
go build -o /tmp/rabbitrun-demo .
xvfb-run -a /tmp/rabbitrun-demo --record-demo /tmp/rabbitrun-long.mp4 \
  --record-char cute --record-seconds 60
ffmpeg -i /tmp/rabbitrun-long.mp4 -vf 'scale=480:-2' -an -c:v libx264 \
  -preset slow -crf 26 -pix_fmt yuv420p -movflags +faststart \
  -map_metadata -1 rabbitrun.mp4
```

The Games page uses GIF-like previews without playback controls. Visible videos
loop silently; scrolling offscreen or hiding the tab pauses them. Reduced-motion
preferences, unavailable autoplay, or disabled JavaScript leave the poster visible.

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
Videos and posters have content-hashed URLs to avoid stale browser caches.
