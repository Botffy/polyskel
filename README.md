This is an implementation, written in Python 2.7, using [pyeuclid](https://github.com/ezag/pyeuclid) for geometry computation, of the straight skeleton algorithm as described by Felkel and Obdržálek in their 1998 conference paper *Straight skeleton implementation*.

This implemetation is a bit crap: it does not handle vertex events (see *Raising Roofs, Crashing Cycles and Playing Pool* by Eppstein and Erickson), so it fails horribly for degenerate polygons, which limits its usefulness.
In addition, Felkel's algorithm itself is rather dated, more efficient (and more correct) approaches are available. 
For a modern and excellent overview of the topic please refer to Stefan Huber's excellent [Computing Straight Skeleton and Motorcycle Graphs: Theory and Practice](https://www.sthu.org/research/publications/files/phdthesis.pdf).

Use `demo.py <example-file>` for a demonstration.

---

OH WOW, this is actually being used!

Check out [Yongha Hwang's fork](https://github.com/yonghah/polyskel) to see polyskel in [real-life action](https://github.com/yonghah/polyskel/blob/master/Create%20layout%20network%20using%20straight%20skeletons%20.ipynb) <3 <3 <3.

So it's not THAT crap, after all.

There is also [a Swift port](https://github.com/andygeers/Polyskel-Swift) available of Yongha Hwang's version.
