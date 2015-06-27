import logging
import heapq
from euclid import *
from itertools import cycle, chain, islice, izip, tee
from collections import namedtuple

log = logging.getLogger("__name__")

class Debug:
	def __init__(self, image):
		if image is not None:
			self.im = image[0]
			self.draw = image[1]
			self.do = True
		else:
			self.do = False

	def line(self, *args, **kwargs):
		if self.do:
			self.draw.line(*args, **kwargs)

	def rectangle(self, *args, **kwargs):
		if self.do:
			self.draw.rectangle(*args, **kwargs)

	def show(self):
		if self.do:
			self.im.show()

_debug = Debug(None)

def set_debug(image):
	global _debug
	_debug = Debug(image)

def _window(lst):
	prevs, items, nexts = tee(lst, 3)
	prevs = islice(cycle(prevs), len(lst)-1, None)
	nexts = islice(cycle(nexts), 1, None)
	return izip(prevs, items, nexts)

def _cross(a, b):
	res = a.x*b.y - b.x*a.y
	return res

def _approximately_equals(a, b):
	return a==b or (abs(a-b) <= max(abs(a), abs(b)) * 0.001)

def _approximately_same(point_a, point_b):
	return _approximately_equals(point_a.x, point_b.x) and _approximately_equals(point_a.y, point_b.y)


class _SplitEvent(namedtuple("_SplitEvent", "distance, intersection_point, vertex, opposite_edge")):
	__slots__ = ()
	def __str__(self):
		return "{} Split event @ {} from {} to {}".format(self.distance, self.intersection_point, self.vertex, self.opposite_edge)

class _EdgeEvent(namedtuple("_EdgeEvent", "distance intersection_point vertex_a vertex_b")):
	__slots__ = ()
	def __str__(self):
		return "{} Edge event @ {} between {} and {}".format(self.distance, self.intersection_point, self.vertex_a, self.vertex_b)

_OriginalEdge = namedtuple("_OriginalEdge", "edge bisector_left, bisector_right")

def _side(point, line):
	a = line.p.x
	b = line.p.y

class _LAVertex:
	def __init__(self, point, edge_left, edge_right, direction_vectors=None):
		self.point = point
		self.edge_left = edge_left
		self.edge_right = edge_right
		self.prev = None
		self.next = None
		self.lav = None
		self._valid = True; # this should be handled better. Maybe membership in lav implies validity?

		creator_vectors = (edge_left.v.normalized()*-1, edge_right.v.normalized())
		if direction_vectors is None:
			direction_vectors = creator_vectors

		self._is_reflex = (_cross(*direction_vectors)) < 0
		self._bisector = Ray2(self.point, operator.add(*creator_vectors) * (-1 if self.is_reflex else 1))
		log.info("Created vertex %s", self.__repr__())
		_debug.line((self.bisector.p.x, self.bisector.p.y, self.bisector.p.x+self.bisector.v.x*100, self.bisector.p.y+self.bisector.v.y*100), fill="blue")

	@property
	def bisector(self):
		return self._bisector

	@property
	def is_reflex(self):
		return self._is_reflex

	def next_event(self):
		events = []
		if self.is_reflex:
			log.debug("looking for split candidates for vertex %s", self)
			for edge in self.lav.original_polygon:
				if edge.edge == self.edge_left or edge.edge == self.edge_right:
					continue

				log.debug("\tconsidering EDGE %s", edge)

				# choose the "less parallel" edge (in order to exclude a potentially parallel edge)
				leftdot = abs(self.edge_left.v.normalized().dot(edge.edge.v.normalized()))
				rightdot = abs(self.edge_right.v.normalized().dot(edge.edge.v.normalized()))
				selfedge = self.edge_left if leftdot < rightdot else self.edge_right
				otheredge = self.edge_left if leftdot > rightdot else self.edge_right
				#selfedge = self.edge_left

				#intersect egde's line with the line of self's edge
				i = Line2(selfedge).intersect(Line2(edge.edge))
				if i is not None and not _approximately_equals(i, self.point):
					#locate candidate b
					linvec = (self.point - i).normalized()
					edvec = edge.edge.v.normalized()
					if linvec.dot(edvec)<0:
						edvec = -edvec

					bisecvec = edvec + linvec
					if abs(bisecvec) == 0:
						continue
					bisector = Line2(i, bisecvec)
					b = bisector.intersect(self.bisector)

					if b is None:
						continue

					#check eligibility of b
					xleft =  _cross(edge.bisector_left.v.normalized(), (b - edge.bisector_left.p).normalized())  > 0
					xright = _cross(edge.bisector_right.v.normalized(), (b - edge.bisector_right.p).normalized())  <  0
					xedge =  _cross(edge.edge.v.normalized(), (b - edge.edge.p).normalized()) < 0

					if not (xleft and xright and xedge):
						log.debug("\t\tDiscarded candidate %s (%s-%s-%s)", b, xleft, xright, xedge)
						continue

					log.debug("\t\tFound valid candidate %s", b)
					events.append( _SplitEvent(Line2(edge.edge).distance(b), b, self, edge.edge) )

		i_prev = self.bisector.intersect(self.prev.bisector)
		i_next = self.bisector.intersect(self.next.bisector)

		if i_prev is not None:
			events.append(_EdgeEvent(Line2(self.edge_left).distance(i_prev), i_prev, self.prev, self))
		if i_next is not None:
			events.append(_EdgeEvent(Line2(self.edge_right).distance(i_next), i_next, self, self.next))

		if not events:
			return None

		ev = min(events, key=lambda event: self.point.distance(event.intersection_point))

		log.info("Generated new event for %s: %s", self, ev)
		return ev

	def invalidate(self):
		self._valid = False
		self.lav = None

	@property
	def is_valid(self):
		return self._valid

	def __str__(self):
		return "Vertex ({:.2f};{:.2f})".format(self.point.x, self.point.y)

	def __repr__(self):
		return "Vertex ({}) ({:.2f};{:.2f}), bisector {}, edges {} {}".format("reflex" if self.is_reflex else "convex", self.point.x, self.point.y, self.bisector, self.edge_left, self.edge_right)

class _SLAV:
	def __init__(self, polygon):
		if not isinstance(polygon[0], Point2):
			polygon = [Point2(float(x), float(y)) for (x,y) in polygon]

		root = _LAV.from_polygon(polygon, self)
		self._lavs = [root]

		#store original polygon for calculating split events
		self._polygon = [_OriginalEdge(LineSegment2(vertex.prev.point, vertex.point), vertex.prev.bisector, vertex.bisector) for vertex in root]


	def handle_edge_event(self, event):
		output = []
		events = []

		if event.vertex_a.prev == event.vertex_b.next:
			log.info("%.2f Peak event at intersection %s from <%s,%s,%s>", event.distance, event.intersection_point, event.vertex_a, event.vertex_b, event.vertex_a.prev)
			self._lavs.remove(event.vertex_a.lav)
			for vertex in event.vertex_a.lav:
				output.append((vertex.point, event.intersection_point))
				vertex.invalidate()
		else:
			log.info("%.2f Edge event at intersection %s from <%s,%s>", event.distance, event.intersection_point, event.vertex_a, event.vertex_b)
			lav = event.vertex_a.lav
			new_vertex = lav.unify(event.vertex_a, event.vertex_b, event.intersection_point)
			for vertex in (event.vertex_a, event.vertex_b):
				output.append((vertex.point, event.intersection_point))
			next_event = new_vertex.next_event()
			if next_event is not None:
				events.append(next_event)

		return (output, events)

	def handle_split_event(self, event):
		log.info("%.2f Split event at intersection %s from vertex %s, for edge %s", event.distance, event.intersection_point, event.vertex, event.opposite_edge)

		output = [(event.vertex.point, event.intersection_point)]
		vertices = []
		x = None
		y = None
		v1 = None
		v2 = None
		norm = event.opposite_edge.v.normalized()
		for v in event.vertex.lav:
			xv1 = None
			xv2 = None
			if norm == v.edge_left.v.normalized() and event.opposite_edge.p == v.edge_left.p:
				# if adding hole handling, don't forget boundchecking
				log.info("Vertex %s holds edge as left edge (%s, %s)", v, xv1, xv2)
				x = v
				y = x.prev
				break
			elif norm == v.edge_right.v.normalized() and event.opposite_edge.p == v.edge_right.p:
				log.info("Vertex %s holds edge as right edge (%s, %s)", v, xv1, xv2)
				y=v
				x=y.next
				break

		if x is None:
			log.error("FAILED split event %s", event)
			return ([], [])

		v1 = _LAVertex(event.intersection_point, event.vertex.edge_left, event.opposite_edge)
		v2 = _LAVertex(event.intersection_point, event.opposite_edge, event.vertex.edge_right)

		idx = self._lavs.index(event.vertex.lav)
		del self._lavs[idx]

		v1.prev = event.vertex.prev
		v1.next = x
		event.vertex.prev.next = v1
		x.prev = v1

		v2.prev = y
		v2.next = event.vertex.next
		event.vertex.next.prev = v2
		y.next = v2

		new_lavs = [_LAV.from_chain(v1, self), _LAV.from_chain(v2, self)]
		for l in new_lavs:
			if len(l) > 2:
				self._lavs.insert(idx, l)
				vertices.append(l.head)
				idx += 1
			else:
				log.info("LAV has collapsed into the line %s--%s", l.head.point, l.head.next.point)
				output.append((l.head.point, l.head.next.point))
				for v in l:
					v.invalidate()

		events = []
		for vertex in vertices:
			next_event = vertex.next_event()
			if next_event is not None:
				events.append(next_event)

		event.vertex.invalidate()
		return (output, events)

	@property
	def original_polygon(self):
		return self._polygon

class _LAV:
	def __init__(self, slav):
		self.head = None
		self._slav = slav
		self._len = 0


	@classmethod
	def from_polygon(cls, polygon, slav):
		lav = cls(slav)

		polygon = [point for prev, point, next in _window(polygon) if not (point==next or (point-prev).normalized() == (next-point).normalized())]

		for prev, point, next in _window(polygon):
			lav._len += 1
			vertex = _LAVertex(point, LineSegment2(prev, point), LineSegment2(point, next))
			vertex.lav = lav
			if lav.head == None:
				lav.head = vertex
				vertex.prev = vertex.next = vertex
			else:
				vertex.next = lav.head
				vertex.prev = lav.head.prev
				vertex.prev.next = vertex
				lav.head.prev = vertex
		return lav

	@classmethod
	def from_chain(cls, head, slav):
		lav = cls(slav)
		lav.head = head
		for vertex in lav:
			lav._len += 1
			vertex.lav = lav
		return lav

	@property
	def original_polygon(self):
		return self._slav.original_polygon

	def unify(self, vertex_a, vertex_b, point):
		replacement =_LAVertex(point, vertex_a.edge_left, vertex_b.edge_right, (vertex_b.bisector.v.normalized(), vertex_a.bisector.v.normalized()))
		replacement.lav = self

		if self.head in [vertex_a, vertex_b]:
			self.head = replacement

		vertex_a.prev.next = replacement
		vertex_b.next.prev = replacement
		replacement.prev = vertex_a.prev
		replacement.next = vertex_b.next

		vertex_a.invalidate()
		vertex_b.invalidate()

		self._len -= 1
		return replacement

	def __len__(self):
		return self._len

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
			print cur.__repr__()
			cur = cur.next
			if cur == self.head:
				break

class _EventQueue:
	def __init__(self):
		self.__data = []

	def put(self, item):
		if item is not None:
			heapq.heappush(self.__data, item)

	def put_all(self, iterable):
		for item in iterable:
			heapq.heappush(self.__data, item)

	def get(self):
		return heapq.heappop(self.__data)

	def empty(self):
		return len(self.__data)==0

	def peek(self):
		return self.__data[0]

	def show(self):
		for item in self.__data:
			print item

def skeletonize(polygon):
	slav = _SLAV(polygon)
	output = []
	prioque = _EventQueue()

	for vertex in slav._lavs[0]: # fixme
		prioque.put(vertex.next_event())

	while not prioque.empty():
		i = prioque.get()
		if isinstance(i, _EdgeEvent):
			if not i.vertex_a.is_valid or not i.vertex_b.is_valid:
				log.info("%.2f Discarded outdated edge event %s", i.distance, i)
				continue

			(arcs, events) = slav.handle_edge_event(i)
		elif isinstance(i, _SplitEvent):
			if not i.vertex.is_valid:
				log.info("%.2f Discarded outdated split event %s", i.distance, i)
				continue
			(arcs, events) = slav.handle_split_event(i)

		prioque.put_all(events)
		output.extend(arcs)
		for arc in arcs:
			_debug.line((arc[0].x, arc[0].y, arc[1].x, arc[1].y), fill="red")

		_debug.show()
	return output

