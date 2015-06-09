from euclid import *
from Queue import PriorityQueue
from itertools import cycle, chain, islice, izip, tee
from collections import namedtuple

def _window(lst):
	prevs, items, nexts = tee(lst, 3)
	prevs = islice(cycle(prevs), len(lst)-1, None)
	nexts = islice(cycle(nexts), 1, None)
	return izip(prevs, items, nexts)


class _LAVertex:
	def __init__(self, point, prev, next, edge_left, edge_right):
		self.point = point
		self.edge_right = edge_right
		self.edge_left = edge_left
		self.prev = prev
		self.next = next
		self._bisector = Ray2(self.point, edge_left.v.normalize() + edge_right.v.normalize())

	@property
	def bisector(self):
		return self._bisector

	def __str__(self):
		return self.point.__str__()


class _LAV:
	def __init__(self, polygon):
		self.head = None

		for prev, point, next in _window(polygon):
			vertex = _LAVertex(point, None, None, LineSegment2(point, prev), LineSegment2(point, next))
			if self.head == None:
				self.head = vertex
				vertex.prev = vertex.next = vertex
			else:
				vertex.next = self.head
				vertex.prev = self.head.prev
				vertex.prev.next = vertex
				self.head.prev = vertex

	def __iter__(self):
		cur = self.head
		while True:
			yield cur
			cur = cur.next
			if cur == self.head:
				raise StopIteration

	def _show(self):
		cur = self.head
		while True:
			print cur
			cur = cur.next
			if cur == self.head:
				break


def skeletonize(polygon):
	lav = _LAV(polygon)
	output = []
	prioque = PriorityQueue()

	Event = namedtuple("Event", "distance intersection_point vertex1 vertex2")

	for vertex in lav:
		i_prev = vertex.bisector.intersect(vertex.prev.bisector)
		i_next = vertex.bisector.intersect(vertex.next.bisector)
		if vertex.point.distance(i_prev) < vertex.point.distance(i_next):
			prioque.put(Event(vertex.point.distance(i_prev), i_prev, vertex, vertex.prev))
		else:
			prioque.put(Event(vertex.point.distance(i_next), i_next, vertex, vertex.next))

	while not prioque.empty():
		i = prioque.get()

		output.append((i.intersection_point, i.vertex1.point))
		output.append((i.intersection_point, i.vertex2.point))
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

	skeleton = skeletonize(poly)
	for res in skeleton:
		print res
	#for line in skeletonize(poly):
	#	draw.line((line[0].x, line[0].y, line[1].x, line[1].y), fill="red")
	#im.show();
