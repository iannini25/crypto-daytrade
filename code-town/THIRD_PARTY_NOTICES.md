# Third-party notices

## Habblaud

Isometric camera behavior (`src/camera.ts`) and the 4-direction A* with a turn
penalty (`src/path.ts`) are adapted from
[marmottajr/habblaud](https://github.com/marmottajr/habblaud) (live demo
https://habblaud.com/en).

```
MIT License

Copyright (c) 2026 Márcio Junior

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

The room art in Code Town is a top-down interior. Habblaud's camera behavior
and pathfinding are reused. Its furniture sprites are not copied: Habblaud
draws its own procedural pixel props, and Code Town draws a separate cozy
set (desks, monitors, chairs, rugs, plants, lamps) in canvas.

## Kenney (CC0)

Floor variety can use tiles from Kenney's Roguelike Indoor pack and Tiny Town,
both Creative Commons Zero. The files and license texts live in
`public/assets/kenney/`.

Roguelike Indoor pack and Tiny Town (1.1) by Kenney Vleugels (www.kenney.nl).
https://creativecommons.org/publicdomain/zero/1.0/

You may use these assets in personal and commercial projects. Credit is
appreciated and not required. The current office draws furniture in canvas
so rooms stay readable; the Kenney sheets are vendored for reuse and credit.

## pixel-agents

The habit of one identifiable pixel character per agent, with a name above
the head and a pose that matches the current task (walking, sitting at a
desk, reading), follows
[pixel-agents-hq/pixel-agents](https://github.com/pixel-agents-hq/pixel-agents).

```
MIT License

Copyright (c) 2026 Pablo De Lucca
```

The full MIT text is the same grant as the Habblaud notice above. No source
files or sprite sheets from that repository are included. Characters, walls,
floors, doors, and furniture in Code Town are drawn in canvas.
