from __future__ import annotations

import csv
import io
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Iterable

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from .models import PhysicalUnit, Placement, PlacementZone, Stock, StockChange
from .services import StockUnderflowError, adjust_stock, move_unit, reconcile_stock


SCHEMA_VERSION = "lab-inventory.operations.v1"
MAX_OPERATIONS = 1000


class ImportValidationError(ValidationError):
    pass


@dataclass(frozen=True)
class ValidatedBatch:
    operations: list[dict]
    preview: list[dict]
    preconditions: dict[str, dict]

    def session_payload(self) -> dict:
        return {
            "schema": SCHEMA_VERSION,
            "operations": self.operations,
            "preconditions": self.preconditions,
        }


def _nonempty(value, field: str, row: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ImportValidationError(f"Row {row}: {field} is required.")
    return text


def _decimal(value, field: str, row: int, *, allow_zero: bool = False) -> Decimal:
    try:
        result = Decimal(str(value).strip())
    except (InvalidOperation, AttributeError, ValueError) as exc:
        raise ImportValidationError(f"Row {row}: {field} must be a number.") from exc
    if result < 0 or (result == 0 and not allow_zero):
        comparator = "non-negative" if allow_zero else "positive"
        raise ImportValidationError(f"Row {row}: {field} must be {comparator}.")
    return result


def _int(value, field: str, row: int, *, default: int = 100) -> int:
    if value in (None, ""):
        return default
    try:
        result = int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ImportValidationError(f"Row {row}: {field} must be an integer.") from exc
    if result < 0:
        raise ImportValidationError(f"Row {row}: {field} cannot be negative.")
    return result


def _normalize_reason(value, row: int) -> str:
    mapping = {
        "purchase": StockChange.Reason.PURCHASE,
        "use": StockChange.Reason.USE,
        "transfer": StockChange.Reason.TRANSFER,
        "other": StockChange.Reason.OTHER,
        "PURCHASE": StockChange.Reason.PURCHASE,
        "USE": StockChange.Reason.USE,
        "TRANSFER": StockChange.Reason.TRANSFER,
        "OTHER": StockChange.Reason.OTHER,
    }
    reason = mapping.get(str(value or "").strip())
    if reason is None:
        raise ImportValidationError(
            f"Row {row}: reason must be purchase, use, transfer, or other."
        )
    return str(reason)


def _decode(uploaded_file) -> str:
    raw = uploaded_file.read()
    if len(raw) > 1_000_000:
        raise ImportValidationError("Import file is larger than the 1 MB V1 limit.")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ImportValidationError("Import files must be UTF-8 encoded.") from exc


def parse_stock_adjust_csv(uploaded_file) -> list[dict]:
    reader = csv.DictReader(io.StringIO(_decode(uploaded_file)))
    required = {"item_code", "holder_code", "operation", "quantity", "reason"}
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        raise ImportValidationError(
            "Stock CSV requires item_code, holder_code, operation, quantity, reason columns."
        )

    operations: list[dict] = []
    for row_number, row in enumerate(reader, start=2):
        operation = _nonempty(row.get("operation"), "operation", row_number).lower()
        if operation not in {"add", "remove"}:
            raise ImportValidationError(f"Row {row_number}: operation must be add or remove.")
        quantity = _decimal(row.get("quantity"), "quantity", row_number)
        operations.append(
            {
                "type": "stock_adjust",
                "item_code": _nonempty(row.get("item_code"), "item_code", row_number),
                "holder_code": _nonempty(row.get("holder_code"), "holder_code", row_number),
                "operation": operation,
                "quantity": str(quantity),
                "reason": _normalize_reason(row.get("reason"), row_number),
                "note": str(row.get("note") or "").strip(),
            }
        )
    return _check_batch_size(operations)


def parse_stock_count_csv(uploaded_file) -> list[dict]:
    reader = csv.DictReader(io.StringIO(_decode(uploaded_file)))
    required = {"item_code", "holder_code", "counted_quantity"}
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        raise ImportValidationError(
            "Inventory-count CSV requires item_code, holder_code, counted_quantity columns."
        )

    operations: list[dict] = []
    for row_number, row in enumerate(reader, start=2):
        quantity = _decimal(
            row.get("counted_quantity"), "counted_quantity", row_number, allow_zero=True
        )
        operations.append(
            {
                "type": "stock_count",
                "item_code": _nonempty(row.get("item_code"), "item_code", row_number),
                "holder_code": _nonempty(row.get("holder_code"), "holder_code", row_number),
                "counted_quantity": str(quantity),
                "note": str(row.get("note") or "").strip(),
            }
        )
    return _check_batch_size(operations)


def parse_placement_csv(uploaded_file) -> list[dict]:
    reader = csv.DictReader(io.StringIO(_decode(uploaded_file)))
    required = {"unit_code"}
    if reader.fieldnames is None or not required.issubset(set(reader.fieldnames)):
        raise ImportValidationError("Placement CSV requires a unit_code column.")

    operations: list[dict] = []
    for row_number, row in enumerate(reader, start=2):
        zone_code = str(row.get("zone_code") or "").strip()
        support_code = str(row.get("support_unit_code") or "").strip()
        if bool(zone_code) == bool(support_code):
            raise ImportValidationError(
                f"Row {row_number}: specify exactly one of zone_code or support_unit_code."
            )
        operations.append(
            {
                "type": "move_unit",
                "unit_code": _nonempty(row.get("unit_code"), "unit_code", row_number),
                "zone_code": zone_code or None,
                "support_unit_code": support_code or None,
                "order_key": _int(row.get("order_key"), "order_key", row_number),
                "note": str(row.get("note") or "").strip(),
            }
        )
    return _check_batch_size(operations)


def parse_operations_json(uploaded_file) -> list[dict]:
    try:
        document = json.loads(_decode(uploaded_file))
    except json.JSONDecodeError as exc:
        raise ImportValidationError(f"Invalid JSON: {exc.msg} at line {exc.lineno}.") from exc

    if not isinstance(document, dict) or document.get("schema") != SCHEMA_VERSION:
        raise ImportValidationError(f"JSON schema must be {SCHEMA_VERSION}.")
    raw_operations = document.get("operations")
    if not isinstance(raw_operations, list):
        raise ImportValidationError("JSON operations must be an array.")

    operations: list[dict] = []
    for row_number, raw in enumerate(raw_operations, start=1):
        if not isinstance(raw, dict):
            raise ImportValidationError(f"Operation {row_number} must be an object.")
        op_type = _nonempty(raw.get("type"), "type", row_number)
        if op_type == "stock_adjust":
            operation = _nonempty(raw.get("operation"), "operation", row_number).lower()
            if operation not in {"add", "remove"}:
                raise ImportValidationError(
                    f"Operation {row_number}: operation must be add or remove."
                )
            quantity = _decimal(raw.get("quantity"), "quantity", row_number)
            operations.append(
                {
                    "type": op_type,
                    "item_code": _nonempty(raw.get("item_code"), "item_code", row_number),
                    "holder_code": _nonempty(raw.get("holder_code"), "holder_code", row_number),
                    "operation": operation,
                    "quantity": str(quantity),
                    "reason": _normalize_reason(raw.get("reason"), row_number),
                    "note": str(raw.get("note") or "").strip(),
                }
            )
        elif op_type == "stock_count":
            quantity = _decimal(
                raw.get("counted_quantity"), "counted_quantity", row_number, allow_zero=True
            )
            operations.append(
                {
                    "type": op_type,
                    "item_code": _nonempty(raw.get("item_code"), "item_code", row_number),
                    "holder_code": _nonempty(raw.get("holder_code"), "holder_code", row_number),
                    "counted_quantity": str(quantity),
                    "note": str(raw.get("note") or "").strip(),
                }
            )
        elif op_type == "move_unit":
            zone_code = str(raw.get("zone_code") or "").strip()
            support_code = str(raw.get("support_unit_code") or "").strip()
            if bool(zone_code) == bool(support_code):
                raise ImportValidationError(
                    f"Operation {row_number}: specify exactly one target parent."
                )
            operations.append(
                {
                    "type": op_type,
                    "unit_code": _nonempty(raw.get("unit_code"), "unit_code", row_number),
                    "zone_code": zone_code or None,
                    "support_unit_code": support_code or None,
                    "order_key": _int(raw.get("order_key"), "order_key", row_number),
                    "note": str(raw.get("note") or "").strip(),
                }
            )
        else:
            raise ImportValidationError(f"Operation {row_number}: unsupported type {op_type}.")

    return _check_batch_size(operations)


def _check_batch_size(operations: list[dict]) -> list[dict]:
    if not operations:
        raise ImportValidationError("Import contains no operations.")
    if len(operations) > MAX_OPERATIONS:
        raise ImportValidationError(f"V1 imports are limited to {MAX_OPERATIONS} operations.")
    return operations


def parse_import(kind: str, uploaded_file) -> list[dict]:
    parsers = {
        "stock_adjust_csv": parse_stock_adjust_csv,
        "stock_count_csv": parse_stock_count_csv,
        "placement_csv": parse_placement_csv,
        "operations_json": parse_operations_json,
    }
    try:
        parser = parsers[kind]
    except KeyError as exc:
        raise ImportValidationError("Unsupported import type.") from exc
    return parser(uploaded_file)


def _stock_key(item_code: str, holder_code: str) -> str:
    return f"stock:{item_code}:{holder_code}"


def _placement_key(unit_code: str) -> str:
    return f"placement:{unit_code}"


def _load_stock(item_code: str, holder_code: str, row: int) -> Stock:
    try:
        return Stock.objects.select_related("item", "holder").get(
            item__code=item_code,
            holder__code=holder_code,
        )
    except Stock.DoesNotExist as exc:
        raise ImportValidationError(
            f"Operation {row}: no stock row for {item_code} in {holder_code}."
        ) from exc


def validate_operations(operations: Iterable[dict], *, user=None) -> ValidatedBatch:
    operations = list(operations)
    preview: list[dict] = []
    preconditions: dict[str, dict] = {}
    simulated_stock: dict[str, Decimal] = {}

    current_parent: dict[str, tuple[str | None, str | None, int]] = {}
    all_placements = Placement.objects.select_related("unit", "zone", "support_unit")
    for placement in all_placements:
        current_parent[placement.unit.code] = (
            placement.zone.code if placement.zone else None,
            placement.support_unit.code if placement.support_unit else None,
            placement.order_key,
        )

    for index, operation in enumerate(operations, start=1):
        op_type = operation["type"]
        if op_type in {"stock_adjust", "stock_count"}:
            if user is not None and not user.has_perm("inventory.change_stock"):
                raise PermissionDenied("This batch contains stock mutations not allowed for this user.")
            stock = _load_stock(operation["item_code"], operation["holder_code"], index)
            key = _stock_key(operation["item_code"], operation["holder_code"])
            if key not in simulated_stock:
                simulated_stock[key] = stock.quantity
                preconditions[key] = {"quantity": str(stock.quantity)}
            before = simulated_stock[key]

            if op_type == "stock_adjust":
                quantity = Decimal(operation["quantity"])
                delta = quantity if operation["operation"] == "add" else -quantity
                after = before + delta
                if after < 0:
                    raise ImportValidationError(
                        f"Operation {index}: {operation['item_code']} in {operation['holder_code']} would become negative."
                    )
                simulated_stock[key] = after
                preview.append(
                    {
                        "index": index,
                        "kind": "在庫増減",
                        "target": f"{operation['item_code']} @ {operation['holder_code']}",
                        "before": str(before),
                        "after": str(after),
                        "detail": f"{operation['operation']} {quantity}",
                    }
                )
            else:
                after = Decimal(operation["counted_quantity"])
                simulated_stock[key] = after
                preview.append(
                    {
                        "index": index,
                        "kind": "棚卸",
                        "target": f"{operation['item_code']} @ {operation['holder_code']}",
                        "before": str(before),
                        "after": str(after),
                        "detail": f"補正 {after - before}",
                    }
                )

        elif op_type == "move_unit":
            if user is not None and not user.has_perm("inventory.change_placement"):
                raise PermissionDenied("This batch contains placement mutations not allowed for this user.")
            try:
                unit = PhysicalUnit.objects.get(code=operation["unit_code"])
            except PhysicalUnit.DoesNotExist as exc:
                raise ImportValidationError(
                    f"Operation {index}: unknown physical unit {operation['unit_code']}."
                ) from exc

            zone_code = operation.get("zone_code")
            support_code = operation.get("support_unit_code")
            if zone_code:
                if not PlacementZone.objects.filter(code=zone_code, is_active=True).exists():
                    raise ImportValidationError(
                        f"Operation {index}: unknown/inactive placement zone {zone_code}."
                    )
            if support_code:
                if support_code == unit.code:
                    raise ImportValidationError(f"Operation {index}: a unit cannot support itself.")
                if not PhysicalUnit.objects.filter(code=support_code, is_active=True).exists():
                    raise ImportValidationError(
                        f"Operation {index}: unknown/inactive support unit {support_code}."
                    )

            key = _placement_key(unit.code)
            if key not in preconditions:
                original = current_parent.get(unit.code, (None, None, 0))
                preconditions[key] = {
                    "zone_code": original[0],
                    "support_unit_code": original[1],
                    "order_key": original[2],
                }

            before = current_parent.get(unit.code, (None, None, 0))
            after = (zone_code, support_code, int(operation["order_key"]))
            current_parent[unit.code] = after
            preview.append(
                {
                    "index": index,
                    "kind": "位置変更",
                    "target": unit.code,
                    "before": _format_parent(before),
                    "after": _format_parent(after),
                    "detail": "通常保管位置",
                }
            )
        else:
            raise ImportValidationError(f"Operation {index}: unsupported operation type.")

    _validate_support_graph(current_parent)
    return ValidatedBatch(operations=operations, preview=preview, preconditions=preconditions)


def _format_parent(parent: tuple[str | None, str | None, int]) -> str:
    zone_code, support_code, order_key = parent
    if zone_code:
        return f"{zone_code} (order {order_key})"
    if support_code:
        return f"on {support_code} (order {order_key})"
    return "未登録"


def _validate_support_graph(parent_map: dict[str, tuple[str | None, str | None, int]]) -> None:
    for start in parent_map:
        visited: set[str] = set()
        current = start
        while current:
            if current in visited:
                raise ImportValidationError(f"Placement batch would create a support cycle involving {current}.")
            visited.add(current)
            parent = parent_map.get(current)
            current = parent[1] if parent else None


def _assert_preconditions(preconditions: dict[str, dict]) -> None:
    for key, expected in preconditions.items():
        if key.startswith("stock:"):
            _, item_code, holder_code = key.split(":", 2)
            stock = _load_stock(item_code, holder_code, 0)
            if str(stock.quantity) != expected["quantity"]:
                raise ImportValidationError(
                    f"Current stock changed after preview: {item_code} @ {holder_code}. Preview again."
                )
        elif key.startswith("placement:"):
            unit_code = key.split(":", 1)[1]
            try:
                placement = Placement.objects.select_related("zone", "support_unit").get(unit__code=unit_code)
                actual = {
                    "zone_code": placement.zone.code if placement.zone else None,
                    "support_unit_code": placement.support_unit.code if placement.support_unit else None,
                    "order_key": placement.order_key,
                }
            except Placement.DoesNotExist:
                actual = {"zone_code": None, "support_unit_code": None, "order_key": 0}
            if actual != expected:
                raise ImportValidationError(
                    f"Current placement changed after preview: {unit_code}. Preview again."
                )


@transaction.atomic
def apply_validated_batch(payload: dict, *, user) -> int:
    if payload.get("schema") != SCHEMA_VERSION:
        raise ImportValidationError("Pending import schema is invalid or expired.")
    operations = payload.get("operations")
    preconditions = payload.get("preconditions")
    if not isinstance(operations, list) or not isinstance(preconditions, dict):
        raise ImportValidationError("Pending import data is invalid or expired.")

    _assert_preconditions(preconditions)
    validate_operations(operations, user=user)

    applied = 0
    for operation in operations:
        if operation["type"] == "stock_adjust":
            stock = _load_stock(operation["item_code"], operation["holder_code"], applied + 1)
            quantity = Decimal(operation["quantity"])
            delta = quantity if operation["operation"] == "add" else -quantity
            try:
                adjust_stock(
                    stock=stock,
                    delta=delta,
                    reason=operation["reason"],
                    note=operation.get("note", ""),
                    actor=user,
                )
            except StockUnderflowError as exc:
                raise ImportValidationError(exc.messages) from exc
        elif operation["type"] == "stock_count":
            stock = _load_stock(operation["item_code"], operation["holder_code"], applied + 1)
            reconcile_stock(
                stock=stock,
                counted_quantity=operation["counted_quantity"],
                note=operation.get("note", ""),
                actor=user,
            )
        elif operation["type"] == "move_unit":
            unit = PhysicalUnit.objects.get(code=operation["unit_code"])
            zone = (
                PlacementZone.objects.get(code=operation["zone_code"])
                if operation.get("zone_code")
                else None
            )
            support = (
                PhysicalUnit.objects.get(code=operation["support_unit_code"])
                if operation.get("support_unit_code")
                else None
            )
            move_unit(
                unit=unit,
                zone=zone,
                support_unit=support,
                order_key=int(operation["order_key"]),
                note=operation.get("note", ""),
                actor=user,
            )
        else:
            raise ImportValidationError("Unsupported pending operation.")
        applied += 1

    return applied
