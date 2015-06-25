import logging
import argparse
import re
import polyskel
from PIL import Image, ImageDraw

if __name__ == "__main__":
	logging.basicConfig()

	argparser = argparse.ArgumentParser()
	argparser.add_argument('polygon_file', metavar="<polygon-file>", type=argparse.FileType('r'), help="text file describing the polygon ('-' for standard input)")
	args = argparser.parse_args()

	im = Image.new("RGB", (650, 650), "white");
	draw = ImageDraw.Draw(im);
	polyskel.set_debug((im, draw))
	polyskel.log.setLevel(logging.WARN)

	polygon_line_pat = re.compile(r"\s*(?P<coord_x>\d+(\.\d+)?)\s*,\s*(?P<coord_y>\d+(\.\d+)?)\s*#?.*")

	poly = []
	for line in args.polygon_file:
		line = line.strip()
		if not line or line.startswith('#'):
			continue

		match = polygon_line_pat.match(line)
		poly.append((float(match.group("coord_x")), float(match.group("coord_y"))))

	if not args.polygon_file.isatty():
		args.polygon_file.close()


	for point, next in zip(poly, poly[1:]+poly[:1]):
		draw.line((point[0], point[1], next[0], next[1]), fill=0)

	skeleton = polyskel.skeletonize(poly)
	for res in skeleton:
		print res

	for line in skeleton:
		draw.line((line[0].x, line[0].y, line[1].x, line[1].y), fill="red")
	im.show();
