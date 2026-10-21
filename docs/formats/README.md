# FbPro98 files

What each Front Page Sports Football Pro '98 file holds, which are masked, and
where the layout changes with the age of a league. Byte layouts live in the
specs linked per file. Sampled from `E:\SIERRA\FbPro98`: the PNFL (custom,
season 2049) and the stock leagues shipped with the game (1992-1997). Each
spec's ImHex pattern (`.hexpat`), and a Hex Workshop pattern (`.hsl`) where
one exists, sits beside it.

## Coaching files (one per team or coach)

- `.ply` play: one `P95` block. Spec: [ply.md](ply.md). Library:
  `fbpro98_play`. Not masked. One layout seen. Holds:
  - 11 player records with pre-snap and after-snap logic boxes.
  - Three category bytes.
- `.pln` game plan: offense and defense layouts differ. Spec:
  [pln.md](pln.md). Library: `fbpro98_gameplan`. Not masked. Holds:
  - `G95`: 86 play slots and play records; a play record is custom (path) or
    stock (offset into `STOCK98.MAP`).
  - `J95`: counts.
  - `S98`: stock map name.
- `.prf` coaching profile: variants are stock profiles (other `F95` size,
  `0x69` trailer) and profiles with embedded game plan blocks; the library
  rejects both. Spec: [prf.md](prf.md). Library: `fbpro98_profile`. Not
  masked. Holds:
  - `F95`: substitutions, category weights, FG range, PAT weights, audibles.
  - `I95` and a trailer.
- `.lg2` team files: per team, the profile and game plan for each half and
  side, as folder + filename. Three layouts by league age: custom, modern
  stock (`STOCK` folder) and old stock (empty folder). Team order is the
  `.lge` order. Spec: [lg2.md](lg2.md). Library:
  `fbpro98_lg2`. Not masked.

## League files (one set per league, in the game folder)

- `.lge` league: a chunk tree, depth-first; team numbers 1..N follow it and
  key every other file. Team and roster chunks masked (below). Spec:
  [lge.md](lge.md). Library: `fbpro98_lge` (conference, division and team
  names; standings; the played games and playoff results), used by
  `generate-schedule`. One layout in every sampled league, nested or grouped
  by chunk kind (five stock files); the 8-12 team stock leagues have a
  one-byte-shorter league chunk. Holds:
  - League: name, base year, next player id.
  - Conferences and divisions.
  - Teams: team name, nickname, abbreviation, stadium, head coach, uniform
    colors, draft profile name.
  - Rosters: player ids and jersey numbers per slot.
  - The schedule with scores.
- `.rst` rosters: the `.lge` roster chunks, byte for byte. Same mask.
- `.pyr` players: every player the league knows. Masked (below). Spec:
  [pyr.md](pyr.md). No library. One layout in every sampled file. The game
  folder also holds `1994.PYR`, `1995.PYR` and `1996.PYR`, the same layout
  for those NFL seasons. Holds, per player:
  - Id, first and last name.
  - Potential and actual ratings (AC AG DI EN HA IN SP ST).
  - Injury.
  - Position group, position and years.
  - Height and weight, only for the newest draft class.
- `.dat` + `.idx` statistics: 20-byte records keyed by type (block +
  category) and id (player or team). Unused fields hold leftover memory. The
  index is a B-tree of 512-byte blocks over (type, id) that points at each
  record. Not masked. Spec: [stats.md](stats.md). Library: `fbpro98_stats`
  (the `.dat` only). Fresh stock leagues ship an empty pair (140 and 512
  bytes). Holds:
  - Blocks: player last game, season and career; team and opponents last
    game and season.
  - Game stats, players and teams: extra points, field goals by distance,
    rushing, passing, receiving, interceptions, punting, punt returns, kick
    returns, fumbles, fumble recoveries, sacks, safeties, tackles and
    two-point conversions.
  - Team only: first downs, third and fourth downs, and game details
    (opponent, penalties, time of possession, score, fumbles lost).
  - Player only: penalties, last game.
  - Honors: Player of the Game and of the Week, All-Pro team, Coach of the
    Year, season awards (MVP, offensive and defensive player of the year,
    rookie of the year), Hall of Fame points and nominees.
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
- `CITIES.DAT`: 128 city records; the team chunk's city index points into
  it. Spec: [cities.md](cities.md). Holds, per city:
  - Name.
  - Weather tables.
  - Stadium name and type.
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
  [pdbtoexcel](../pdbtoexcel.md#how-it-works).

## Masks

Full description with worked examples: [pnfl-formats.md](../research/pnfl-formats.md) section 2.

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
