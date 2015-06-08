from euclid import *
from Queue import PriorityQueue
from itertools import cycle, chain, islice, izip, tee


def _window(lst):
	prevs, items, nexts = tee(lst, 3)
	prevs = islice(cycle(prevs), len(lst)-1, None)
	nexts = islice(cycle(nexts), 1, None)
	return izip(prevs, items, nexts)

class _Vertex:
	def __init__(self, point, prev, next):
		self.point = point
		self.vec_prev = point.connect(prev).v.normalize()
		self.vec_next = point.connect(next).v.normalize()
		self.bisector = Ray2(self.point, self.vec_prev + self.vec_next)

	def __eq__(self, other):
		return self.point == other.point
	def __ne__(self, other):
		return not self.__eq__(other)

class _Intersection:
	def __init__(self, point, origin_left, origin_right):
		self.point = point
		self.origin = [origin_left, origin_right]

def skeletonize(polygon):
	output = []
	lav = []
	prioque = PriorityQueue()

	for prev, point, next in _window(polygon):
		lav.append(_Vertex(point, prev, next))

	for prev, vertex, next in _window(lav):
		i_prev = vertex.bisector.intersect(prev.bisector)
		i_next = vertex.bisector.intersect(next.bisector)
		if vertex.point.distance(i_prev) < vertex.point.distance(i_next):
			prioque.put((vertex.point.distance(i_prev), i_prev, vertex, prev))
		else:
			prioque.put((vertex.point.distance(i_next), i_next, vertex, next))

	while not prioque.empty():
		i = prioque.get()
	return output


if __name__ == "__main__":
	import Image, ImageDraw

	poly = [
		Point2(30., 20.),
		Point2(30., 120.),
		Point2(160., 140.),
		Point2(160., 20.),
	]


	im = Image.new("RGB", (200, 200), "white");
	draw = ImageDraw.Draw(im);

	for point, next in zip(poly, poly[1:]+poly[:1]):
		draw.line((point.x, point.y, next.x, next.y), fill=0)

	#skeleton = skeletonize(poly)
	#for point, next in zip(skeleton, skeleton[1:]+skeleton[:1]):
	#	draw.line((point.x, point.y, next.x, next.y), fill=0)

	for line in skeletonize(poly):
		draw.line((line[0].x, line[0].y, line[1].x, line[1].y), fill="red")
	im.show();
