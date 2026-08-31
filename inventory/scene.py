from __future__ import annotations

from collections import defaultdict
from math import floor

from .models import Fixture, PhysicalUnit, Placement, PlacementZone, Room

ROOM_DEFAULT_MM = (8000.0, 6000.0, 2800.0)
FIXTURE_DEFAULT_MM = {
    Fixture.Kind.RACK: (1200.0, 450.0, 1800.0),
    Fixture.Kind.DESK: (1500.0, 700.0, 750.0),
    Fixture.Kind.WALL: (1800.0, 80.0, 1800.0),
    Fixture.Kind.CABINET: (900.0, 450.0, 1800.0),
    Fixture.Kind.WORKBENCH: (1800.0, 800.0, 850.0),
    Fixture.Kind.OTHER: (800.0, 600.0, 800.0),
}
UNIT_DEFAULT_MM = {
    PhysicalUnit.Kind.CONTAINER: (300.0, 220.0, 150.0),
    PhysicalUnit.Kind.CARTON: (400.0, 300.0, 250.0),
    PhysicalUnit.Kind.EQUIPMENT: (300.0, 250.0, 180.0),
    PhysicalUnit.Kind.TOOL: (220.0, 80.0, 50.0),
    PhysicalUnit.Kind.OTHER: (250.0, 200.0, 150.0),
}
AUTO_GAP_MM = 35.0
AUTO_MARGIN_MM = 20.0


def _number(value, fallback: float) -> float:
    return float(value) if value is not None else fallback


def _dimensions(instance, fallback: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        max(1.0, _number(instance.width_mm, fallback[0])),
        max(1.0, _number(instance.depth_mm, fallback[1])),
        max(1.0, _number(instance.height_mm, fallback[2])),
    )


def _fixture_origin(
    fixture: Fixture,
    *,
    index: int,
    room_size: tuple[float, float, float],
    fixture_size: tuple[float, float, float],
) -> tuple[tuple[float, float, float], bool]:
    explicit = fixture.x_mm is not None and fixture.y_mm is not None
    if explicit:
        return (
            _number(fixture.x_mm, 0.0),
            _number(fixture.y_mm, 0.0),
            _number(fixture.z_mm, 0.0),
        ), False

    room_width, room_depth, _ = room_size
    fixture_width, fixture_depth, _ = fixture_size
    cell_width = max(900.0, fixture_width + 250.0)
    cell_depth = max(800.0, fixture_depth + 250.0)
    columns = max(1, floor(max(1.0, room_width - 400.0) / cell_width))
    column = index % columns
    row = index // columns
    x = min(200.0 + column * cell_width, max(0.0, room_width - fixture_width))
    y = min(200.0 + row * cell_depth, max(0.0, room_depth - fixture_depth))
    return (x, y, _number(fixture.z_mm, 0.0)), True


def _zone_geometry(
    zone: PlacementZone,
    *,
    fixture_origin: tuple[float, float, float],
    fixture_size: tuple[float, float, float],
    level_count: int,
    fallback_level: int,
) -> tuple[tuple[float, float, float], tuple[float, float, float], bool]:
    fx, fy, fz = fixture_origin
    fw, fd, fh = fixture_size
    inferred = False

    if zone.kind == PlacementZone.Kind.VOLUME:
        level = zone.level_order or fallback_level
        pitch = fh / max(2, level_count + 1)
        default_z = max(0.0, level * pitch)
        width = _number(zone.width_mm, max(80.0, fw - 40.0))
        depth = _number(zone.depth_mm, max(80.0, fd - 40.0))
        height = _number(zone.height_mm, max(100.0, pitch - 45.0))
        x = _number(zone.x_mm, 20.0 if fw > 40.0 else 0.0)
        y = _number(zone.y_mm, 20.0 if fd > 40.0 else 0.0)
        z = _number(zone.z_mm, default_z)
        inferred = any(
            value is None
            for value in (
                zone.width_mm,
                zone.depth_mm,
                zone.height_mm,
                zone.x_mm,
                zone.y_mm,
                zone.z_mm,
            )
        )
        return (fx + x, fy + y, fz + z), (width, depth, height), inferred

    if zone.kind == PlacementZone.Kind.SURFACE:
        width = _number(zone.width_mm, fw)
        depth = _number(zone.depth_mm, fd)
        height = _number(zone.height_mm, 25.0)
        x = _number(zone.x_mm, 0.0)
        y = _number(zone.y_mm, 0.0)
        z = _number(zone.z_mm, fh)
        inferred = any(
            value is None
            for value in (zone.width_mm, zone.depth_mm, zone.height_mm, zone.z_mm)
        )
        return (fx + x, fy + y, fz + z), (width, depth, height), inferred

    if zone.kind == PlacementZone.Kind.WALL:
        width = _number(zone.width_mm, fw)
        depth = _number(zone.depth_mm, 25.0)
        height = _number(zone.height_mm, fh)
        x = _number(zone.x_mm, 0.0)
        y = _number(zone.y_mm, fd)
        z = _number(zone.z_mm, 0.0)
        inferred = any(
            value is None
            for value in (zone.width_mm, zone.depth_mm, zone.height_mm, zone.y_mm)
        )
        return (fx + x, fy + y, fz + z), (width, depth, height), inferred

    width = _number(zone.width_mm, 80.0)
    depth = _number(zone.depth_mm, 80.0)
    height = _number(zone.height_mm, 80.0)
    x = _number(zone.x_mm, fw / 2.0 - width / 2.0)
    y = _number(zone.y_mm, fd)
    z = _number(zone.z_mm, fh / 2.0 - height / 2.0)
    inferred = any(
        value is None
        for value in (zone.width_mm, zone.depth_mm, zone.height_mm, zone.x_mm, zone.y_mm, zone.z_mm)
    )
    return (fx + x, fy + y, fz + z), (width, depth, height), inferred


def _auto_horizontal_origins(
    placements: list[Placement],
    *,
    parent_origin: tuple[float, float, float],
    parent_size: tuple[float, float, float],
    base_z: float,
) -> dict[object, tuple[float, float, float]]:
    px, py, _ = parent_origin
    pw, pd, _ = parent_size
    left = px + AUTO_MARGIN_MM
    front = py + AUTO_MARGIN_MM
    right = px + max(AUTO_MARGIN_MM, pw - AUTO_MARGIN_MM)
    back = py + max(AUTO_MARGIN_MM, pd - AUTO_MARGIN_MM)

    cursor_x = left
    cursor_y = front
    row_depth = 0.0
    result: dict[object, tuple[float, float, float]] = {}

    for placement in placements:
        unit_size = _dimensions(placement.unit, UNIT_DEFAULT_MM[placement.unit.kind])
        uw, ud, _ = unit_size

        if placement.offset_x_mm is not None or placement.offset_y_mm is not None:
            x = px + _number(placement.offset_x_mm, 0.0)
            y = py + _number(placement.offset_y_mm, 0.0)
        else:
            if cursor_x > left and cursor_x + uw > right:
                cursor_x = left
                cursor_y += row_depth + AUTO_GAP_MM
                row_depth = 0.0
            if cursor_y + ud > back and cursor_y > front:
                cursor_y = front
            x = cursor_x
            y = cursor_y
            cursor_x += uw + AUTO_GAP_MM
            row_depth = max(row_depth, ud)

        z = base_z + _number(placement.offset_z_mm, 0.0)
        result[placement.unit_id] = (x, y, z)

    return result


def _auto_wall_origins(
    placements: list[Placement],
    *,
    parent_origin: tuple[float, float, float],
    parent_size: tuple[float, float, float],
) -> dict[object, tuple[float, float, float]]:
    px, py, pz = parent_origin
    pw, pd, ph = parent_size
    cursor_x = px + AUTO_MARGIN_MM
    cursor_z = pz + AUTO_MARGIN_MM
    row_height = 0.0
    max_x = px + max(AUTO_MARGIN_MM, pw - AUTO_MARGIN_MM)
    max_z = pz + max(AUTO_MARGIN_MM, ph - AUTO_MARGIN_MM)
    result: dict[object, tuple[float, float, float]] = {}

    for placement in placements:
        uw, ud, uh = _dimensions(placement.unit, UNIT_DEFAULT_MM[placement.unit.kind])
        if placement.offset_x_mm is not None or placement.offset_z_mm is not None:
            x = px + _number(placement.offset_x_mm, 0.0)
            z = pz + _number(placement.offset_z_mm, 0.0)
        else:
            if cursor_x > px + AUTO_MARGIN_MM and cursor_x + uw > max_x:
                cursor_x = px + AUTO_MARGIN_MM
                cursor_z += row_height + AUTO_GAP_MM
                row_height = 0.0
            if cursor_z + uh > max_z and cursor_z > pz + AUTO_MARGIN_MM:
                cursor_z = pz + AUTO_MARGIN_MM
            x = cursor_x
            z = cursor_z
            cursor_x += uw + AUTO_GAP_MM
            row_height = max(row_height, uh)

        y = py + pd + _number(placement.offset_y_mm, 0.0)
        result[placement.unit_id] = (x, y, z)

    return result


def build_room_scene(room: Room) -> dict:
    """Build JSON-serializable approximate scene geometry from operational SoT rows."""

    room_size = _dimensions(room, ROOM_DEFAULT_MM)
    warnings: list[str] = []
    if any(value is None for value in (room.width_mm, room.depth_mm, room.height_mm)):
        warnings.append(f"{room.code}: room dimensions are incomplete; placeholder dimensions are used.")

    fixtures = list(room.fixtures.filter(is_active=True).order_by("code"))
    fixture_nodes: list[dict] = []
    zone_nodes: list[dict] = []
    zone_geometry_by_id: dict[object, dict] = {}

    for fixture_index, fixture in enumerate(fixtures):
        fixture_size = _dimensions(fixture, FIXTURE_DEFAULT_MM[fixture.kind])
        fixture_origin, auto_position = _fixture_origin(
            fixture,
            index=fixture_index,
            room_size=room_size,
            fixture_size=fixture_size,
        )
        auto_size = any(value is None for value in (fixture.width_mm, fixture.depth_mm, fixture.height_mm))
        if auto_position:
            warnings.append(f"{fixture.code}: position is incomplete; an automatic display position is used.")

        fixture_nodes.append(
            {
                "code": fixture.code,
                "name": fixture.name,
                "kind": fixture.kind,
                "origin_mm": fixture_origin,
                "size_mm": fixture_size,
                "rotation_z_deg": _number(fixture.rotation_z_deg, 0.0),
                "auto_geometry": auto_position or auto_size,
            }
        )

        zones = list(fixture.zones.filter(is_active=True).order_by("level_order", "code"))
        level_count = max(
            [zone.level_order or 0 for zone in zones] + [len([zone for zone in zones if zone.kind == PlacementZone.Kind.VOLUME]), 1]
        )
        for zone_index, zone in enumerate(zones, start=1):
            origin, size, inferred = _zone_geometry(
                zone,
                fixture_origin=fixture_origin,
                fixture_size=fixture_size,
                level_count=level_count,
                fallback_level=zone_index,
            )
            node = {
                "code": zone.code,
                "name": zone.name,
                "kind": zone.kind,
                "fixture_code": fixture.code,
                "level_order": zone.level_order,
                "origin_mm": origin,
                "size_mm": size,
                "auto_geometry": inferred,
            }
            zone_nodes.append(node)
            zone_geometry_by_id[zone.id] = node

    placements = list(
        Placement.objects.filter(unit__is_active=True)
        .select_related("unit", "zone__fixture__room", "support_unit")
        .order_by("order_key", "unit__code")
    )
    roots_by_zone: dict[object, list[Placement]] = defaultdict(list)
    children_by_support: dict[object, list[Placement]] = defaultdict(list)
    for placement in placements:
        if placement.zone_id and placement.zone_id in zone_geometry_by_id:
            roots_by_zone[placement.zone_id].append(placement)
        elif placement.support_unit_id:
            children_by_support[placement.support_unit_id].append(placement)

    unit_nodes: list[dict] = []
    placed_unit_ids: set[object] = set()
    fallback_unit_count = 0

    def append_unit_tree(
        placement: Placement,
        *,
        origin: tuple[float, float, float],
        root_zone_code: str,
        recursion_path: set[object],
    ) -> None:
        nonlocal fallback_unit_count
        if placement.unit_id in recursion_path or placement.unit_id in placed_unit_ids:
            return

        unit = placement.unit
        unit_size = _dimensions(unit, UNIT_DEFAULT_MM[unit.kind])
        auto_size = any(value is None for value in (unit.width_mm, unit.depth_mm, unit.height_mm))
        if auto_size:
            fallback_unit_count += 1

        node = {
            "code": unit.code,
            "name": unit.name,
            "kind": unit.kind,
            "origin_mm": origin,
            "size_mm": unit_size,
            "rotation_z_deg": _number(placement.rotation_z_deg, 0.0),
            "root_zone_code": root_zone_code,
            "support_unit_code": placement.support_unit.code if placement.support_unit_id else None,
            "auto_geometry": auto_size,
        }
        unit_nodes.append(node)
        placed_unit_ids.add(unit.id)

        children = sorted(
            children_by_support.get(unit.id, []),
            key=lambda child: (child.order_key, child.unit.code),
        )
        if not children:
            return

        child_origins = _auto_horizontal_origins(
            children,
            parent_origin=origin,
            parent_size=unit_size,
            base_z=origin[2] + unit_size[2],
        )
        next_path = recursion_path | {unit.id}
        for child in children:
            append_unit_tree(
                child,
                origin=child_origins[child.unit_id],
                root_zone_code=root_zone_code,
                recursion_path=next_path,
            )

    for zone in zone_nodes:
        zone_id = next((key for key, value in zone_geometry_by_id.items() if value is zone), None)
        if zone_id is None:
            continue
        roots = sorted(roots_by_zone.get(zone_id, []), key=lambda placement: (placement.order_key, placement.unit.code))
        if not roots:
            continue

        zone_origin = tuple(zone["origin_mm"])
        zone_size = tuple(zone["size_mm"])
        if zone["kind"] in (PlacementZone.Kind.WALL, PlacementZone.Kind.ANCHOR):
            origins = _auto_wall_origins(roots, parent_origin=zone_origin, parent_size=zone_size)
        else:
            base_z = zone_origin[2]
            if zone["kind"] == PlacementZone.Kind.SURFACE:
                base_z += zone_size[2]
            origins = _auto_horizontal_origins(
                roots,
                parent_origin=zone_origin,
                parent_size=zone_size,
                base_z=base_z,
            )

        for root in roots:
            append_unit_tree(
                root,
                origin=origins[root.unit_id],
                root_zone_code=zone["code"],
                recursion_path=set(),
            )

    if fallback_unit_count:
        warnings.append(
            f"{fallback_unit_count} physical unit(s) use placeholder dimensions in this 3D view."
        )

    return {
        "schema": "lab-inventory.scene.v1",
        "coordinate_system": {
            "unit": "mm",
            "x": "room width / right",
            "y": "room depth / back",
            "z": "height / up",
        },
        "room": {
            "code": room.code,
            "name": room.name,
            "size_mm": room_size,
        },
        "fixtures": fixture_nodes,
        "zones": zone_nodes,
        "units": unit_nodes,
        "warnings": warnings,
    }
