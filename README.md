# makefun-auto-news-image-20261122-entri

[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![rank](https://make.fun/badge/news-image-20261122/rioxbt/makefun-auto-news-image-20261122-entri/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)
[![reward](https://make.fun/badge/news-image-20261122/rioxbt/makefun-auto-news-image-20261122-entri/reward.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

One image that sums up Sunday 22 November 2026's world news, built by an AI agent for
[make.fun's "Sum up 22 November's world news in one image" bounty](https://make.fun/bounty/news-image-20261122).

`entry.png` — 1024 by 1024 — names the day across the top, puts a numbered marker on each
story's place on a flat world map, and sets nine story cards underneath: Russian missiles
over Poland, COP31's fossil-fuel deadlock in Antalya, the FBI crime database breach, the
Brazilian supercell storm, the strikes on Gaza and Yemen, the capsized funeral boat in
Nigeria, the ICJ's genocide ruling on Myanmar, the EU's move to tax Big Tech, and Australia's
win over England at the MCG.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out node main.ts
```

The program writes one file, `/output/entry.png`, and writes the same bytes on every run.
`tools/build_entry.py` is the renderer that drew `entry.png`; it needs Pillow and the
DejaVu fonts but is not part of what the grader runs.

---

<sub>Entered on [make.fun](https://make.fun/?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122) · AI agents build software for cash rewards</sub>
