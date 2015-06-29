This is a partial implementation, written in Python 2.7, using [pyeuclid](https://github.com/ezag/pyeuclid) for geometry computation, of the straight skeleton algorithm as described by Felkel and Obdržálek in their 1998 conference paper *Straight skeleton implementation*.

This implemetation is a bit crap: it does not handle vertex events (see *Raising Roofs, Crashing Cycles and Playing Pool* by Eppstein and Erickson), so it fails horribly for degenerate polygons, which limits its usefulness.
Also, I'm not quite sure about its robustness.

Use `demo.py <example-file>` for a demonstration.
