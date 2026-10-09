# FbPro98 files

What each Front Page Sports Football Pro '98 file holds, which are masked, and
where the layout changes with the age of a league. Byte layouts live in the
specs linked per file. Sampled from `E:\SIERRA\FbPro98`: the PNFL (custom,
season 2049) and the stock leagues shipped with the game (1992-1997).

## Coaching files (one per team or coach)

- `.ply` play: one `P95` block; 11 player records with pre-snap, play and
  end-of-play logic boxes; three category bytes. Spec:
  [ply.md](../fbpro98_play/specs/ply.md). Library: `fbpro98_play`. Not masked.
  One layout seen.
- `.pln` game plan: `G95` (86 play slots and play records), `J95` (counts),
  `S98` (stock map name). Offense and defense layouts differ; a play record is
  custom (path) or stock (offset into `STOCK98.MAP`). Spec:
  [pln.md](../fbpro98_gameplan/specs/pln.md). Library: `fbpro98_gameplan`.
  Not masked.
- `.prf` coaching profile: `F95` (substitutions, category weights, FG range,
  PAT weights, audibles), `I95`, trailer. Variants: stock profiles (other
  `F95` size, `0x69` trailer) and profiles with embedded game plan blocks; the
  library rejects both. Spec: [prf.md](../fbpro98_profile/specs/prf.md).
  Library: `fbpro98_profile`. Not masked.
- `.lg2` team files: per team, the profile and game plan for each half and
  side, as folder + filename. Three layouts by league age: custom, modern
  stock (`STOCK` folder) and old stock (empty folder). Team order is the
  `.lge` order. Spec: [lg2.md](../fbpro98_lg2/specs/lg2.md). Library:
  `fbpro98_lg2` (custom only). Not masked.

## League files (one set per league, in the game folder)

- `.lge` league: name, base year, next player id, conferences, divisions,
  teams (team name, nickname, abbreviation, stadium, head coach, uniform
  colors, draft profile name), rosters (player ids and jersey numbers per slot) and the schedule with
  scores. Chunk tree, depth-first; team numbers 1..N follow it and key every
  other file. Team and roster chunks masked (below). Spec:
  [lge.md](../fbpro98_lge/specs/lge.md). No library. One layout in every
  sampled league; the 8-12 team stock leagues have a one-byte-shorter league
  chunk.
- `.rst` rosters: the `.lge` roster chunks, byte for byte. Same mask.
- `.pyr` players: every player the league knows: id, first and last name,
  potential and actual ratings (AC AG DI EN HA IN SP ST), injury, position
  group, position, years; height and weight only for the newest draft class.
  Masked (below). Spec: [pyr.md](../fbpro98_pyr/specs/pyr.md). No library.
  One layout in every sampled file. The game folder also holds `1994.PYR`,
  `1995.PYR` and `1996.PYR`, the same layout for those NFL seasons.
- `.dat` + `.idx` statistics: 20-byte records keyed by type and id. Type =
  block + category; blocks for a player's last game, season and career and a
  team's own and opponents' last game and season; categories for field goals,
  rushing, passing, receiving, interceptions, punting, returns, fumbles,
  sacks and tackles (some unmapped). Unused fields hold leftover memory. The
  index is a 512-byte-block tree over (id, type) whose offsets land one record
  late; scanning `.dat` is enough. Not masked. Research:
  [pnfl-formats.md](research/pnfl-formats.md). Fresh stock leagues ship
  an empty pair (140 and 512 bytes).
- `.PYF` free agents: `PPD:` chunk of player ids. `.PYC`: same shape, empty,
  or a 0-byte file. Not masked.
- `.dft` draft order: `DOD:` chunk, team count, then the team numbers in draft
  order. Not masked.
- `.tmn`: 89 (team, player id) pairs in the PNFL, some stale; purpose unknown.
  Only the PNFL has one. Not masked.
- `.lgc` championships: one 36-byte record per season: winner, score, loser,
  score. Not masked.

## Other game data (game folder)

- `STOCK98.DAT` + `STOCK98.MAP`: stock play archive and its `ZTA:` index of
  play names with offsets; `.pln` stock plays point into the map.
- `<TEAM>.DAT` + `<TEAM>.MAP` (`BRONCOS`, `49ERS`, ...): per-team stock
  playbooks, same pair.
- `CITIES.DAT`: 128 city records (name, weather tables, stadium name and
  type); the team chunk's city index points into it. Spec:
  [cities.md](../fbpro98_cities/specs/cities.md).
- `NAMEF.DAT`, `NAMEL.DAT`: NUL-separated first and last names for generated
  players.
- `injury.dat`: offset table plus injury names ("Sprained ankle").
- `msg.dat`: offset table plus game messages.
- `training.dat`: text; training camp settings.
- `CALENDER.DAT` (`SPC:`, `SWC:` chunks), `STPL.DAT` (`SCT:` chunk): not
  mapped.
- `ServerInfo.dat`: text; online play addresses.
- `FILE.DAT`, `ANIM8.DAT`, `ANIM16.DAT`: game resources, not league data.

## Not game files

- `.pdb`: WinLogStats database of game stats, read by `convert-pdb`. Docs:
  [pdbtoexcel](../pdbtoexcel/ARCHITECTURE.md).

## Masks

Full description with worked examples: [pnfl-formats.md](research/pnfl-formats.md) section 2.

- Running XOR (`.lge` team and roster chunks, `.rst`): byte `i` of the chunk
  body XOR `(0x69 × team + i) mod 256`; the team number sits in clear at the
  front of the chunk. Zero bytes read as values stepping by 1.
- Byte substitution (`.pyr`): one 256-entry table per file, applied to every
  record byte; rebuilt from the id bytes at the start of each record.
- Nothing else is masked. Leftover memory after strings (`.lge`, `.lg2`) and
  in unused stat fields (`.dat`) is noise, not a mask.

## Layouts by league age

- `.lg2`: custom, modern stock (1996-1997) and old stock (1995 and earlier)
  differ in the folder field.
- `.prf`: stock profiles differ from saved ones; some saved profiles embed a
  game plan.
- `.pln`: one layout; stock and custom play records differ inside it.
- `.lge`, `.rst`, `.pyr`, `.PYF`, `.dft`, `.lgc`: one layout from the 1992
  stock leagues to the PNFL.
- `.dat` + `.idx`: empty until games are played.
- `.ply`: one layout seen.
