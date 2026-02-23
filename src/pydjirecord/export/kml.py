"""KML export."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, BinaryIO
from xml.etree.ElementTree import Element, ElementTree, SubElement

if TYPE_CHECKING:
    from ..frame import Frame
    from ..layout.details import Details

_KML_NS = "http://www.opengis.net/kml/2.2"


def export_kml(frames: list[Frame], details: Details, output: BinaryIO = sys.stdout.buffer) -> None:
    """Export frames as a KML Document with LineString track."""
    kml = Element("kml", xmlns=_KML_NS)
    doc = SubElement(kml, "Document")
    pm = SubElement(doc, "Placemark")

    name = SubElement(pm, "name")
    name.text = details.aircraft_name or "Flight Track"

    ls = SubElement(pm, "LineString")

    alt_mode = SubElement(ls, "altitudeMode")
    alt_mode.text = "absolute"

    coords_parts: list[str] = []
    for f in frames:
        if f.osd.latitude != 0.0 or f.osd.longitude != 0.0:
            coords_parts.append(f"{f.osd.longitude},{f.osd.latitude},{f.osd.altitude}")

    coords = SubElement(ls, "coordinates")
    coords.text = "\n".join(coords_parts)

    tree = ElementTree(kml)
    tree.write(output, encoding="utf-8", xml_declaration=True)
