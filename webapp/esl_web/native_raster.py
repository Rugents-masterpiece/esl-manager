"""Static rectangle rasters for native ESL components, without imaging dependencies."""
from __future__ import annotations

import struct
import zlib


def _chunk(kind, payload):
    return (struct.pack('>I', len(payload)) + kind + payload
            + struct.pack('>I', zlib.crc32(kind + payload)))


def _rectangle_png(rectangle, holes):
    width, height = rectangle['width'], rectangle['height']
    pixel = bytes.fromhex(rectangle['background'][1:]) + b'\xff'
    raw = bytearray()
    for y in range(height):
        row = bytearray(pixel * width)
        for left, top, right, bottom in holes:
            if top <= y < bottom:
                row[4 * left:4 * right] = b'\x00' * (4 * (right - left))
        raw.append(0)  # PNG filter type: None.
        raw.extend(row)
    return (b'\x89PNG\r\n\x1a\n'
            + _chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
            + _chunk(b'IDAT', zlib.compress(raw))
            + _chunk(b'IEND', b''))


def _intersection(first, second):
    left, top = max(first['x'], second['x']), max(first['y'], second['y'])
    right = min(first['x'] + first['width'], second['x'] + second['width'])
    bottom = min(first['y'] + first['height'], second['y'] + second['height'])
    if left < right and top < bottom:
        return left, top, right, bottom
    return None


def _text_background(text, rectangles):
    if text['background'] != 'transparent':
        return text['background']
    left, top = text['x'], text['y']
    right, bottom = left + text['width'], top + text['height']
    xs, ys = {left, right}, {top, bottom}
    layers = []
    for rectangle in rectangles:
        bounds = _intersection(text, rectangle)
        if bounds is not None:
            il, it, ir, ib = bounds
            xs.update((il, ir))
            ys.update((it, ib))
            layers.append((bounds, rectangle['background']))
    # Rectangle edges partition the box into cells of constant visible color.
    # Sample each cell, not just corners or fully containing rectangles.
    colors = set()
    for y in sorted(ys)[:-1]:
        for x in sorted(xs)[:-1]:
            color = '#ffffff'
            for (il, it, ir, ib), background in reversed(layers):
                if il <= x < ir and it <= y < ib:
                    color = background
                    break
            colors.add(color)
            if len(colors) > 1:
                raise ValueError(f"Text {text['id']!r} has a nonuniform preceding-rectangle background")
    return colors.pop()


def prepare_native_raster(validated_document):
    """Prepare a document already accepted by ``DraftService.validate``.

    ``rectangles`` maps original rectangle IDs to exact-size RGBA PNGs. Each
    rectangle is cut to alpha zero under ALL later text boxes and rectangles.
    ``text_backgrounds`` maps EVERY text ID to its native RGB hex fill: an
    explicit background wins; otherwise the visible preceding rectangle stack
    must be uniform across its box, using white for uncovered pixels.
    ``white_backgrounds`` is the white-foreground subset, kept for compatibility.

    Source order determines backgrounds and holes, never native z-index.
    Bounds are half-open. Input fields are unchanged; other element types are
    left to the translator. Raise ValueError with the source ID for nonzero
    borders, transparent rectangles, or nonuniform inferred text backgrounds.
    This is a rectangle/text adapter, not a general scene renderer.
    """
    rectangles = []
    text_backgrounds = {}
    white_backgrounds = {}
    holes = {}
    for element in validated_document['elements']:
        if element['border_width'] != 0:
            raise ValueError(f"Element {element['id']!r} has an unsupported nonzero border_width")
        if element['type'] in ('rectangle', 'text'):
            for rectangle in rectangles:
                bounds = _intersection(element, rectangle)
                if bounds is not None:
                    il, it, ir, ib = bounds
                    rx, ry = rectangle['x'], rectangle['y']
                    holes[rectangle['id']].append((il - rx, it - ry, ir - rx, ib - ry))
        if element['type'] == 'rectangle':
            if element['background'] == 'transparent':
                raise ValueError(f"Rectangle {element['id']!r} has an unsupported transparent background")
            rectangles.append(element)
            holes[element['id']] = []
        elif element['type'] == 'text':
            background = _text_background(element, rectangles)
            text_backgrounds[element['id']] = background
            if element['color'] == '#ffffff':
                white_backgrounds[element['id']] = background
    return {
        'rectangles': {rectangle['id']: _rectangle_png(rectangle, holes[rectangle['id']])
                       for rectangle in rectangles},
        'text_backgrounds': text_backgrounds,
        'white_backgrounds': white_backgrounds,
    }
