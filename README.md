This is a partial implementation, written in Python 2.7, using [https://github.com/ezag/pyeuclid](pyeuclid) for geometry computation, of the straight skeleton algorithm as described by Felkel and Štěpán Obdržálek in their 1998 conference paper *Straight skeleton implementation*.

This implemetation is a bit crap: it doesn't handle polygons with holes, and even though it does attempt to handle vertex events (described in *Raising Roofs, Crashing Cycles and Playing Pool* by Eppstein and Erickson), it does so pretty half-heartedly, really just to cover the basics.
