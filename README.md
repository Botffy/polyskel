This is a partial implementation, written in Python 2.7, using (https://github.com/ezag/pyeuclid)[pyeuclid] for geometry computation, of the straight skeleton algorithm as described by Felkel and Obdržálek in their 1998 conference paper *Straight skeleton implementation*.

This implemetation is a bit crap: it doesn't handle polygons with holes, and it fails horribly for degenerate polygons (see *Raising Roofs, Crashing Cycles and Playing Pool* by Eppstein and Erickson). Also, I'm not sure about its robustness.

Use `demo.py <example-file>` for a demonstration.
