# Structured import and export

## Role

Structured files are secondary operational interfaces. They do not replace the operational datastore as the source of truth.

Normal one-off changes should use the GUI. Structured import is for bulk operations, inventory counts, migrations, and machine-oriented interchange.

## V1 supported formats

V1 deliberately uses Python-standard-library formats so importing operational changes does not add another runtime/toolchain dependency.

### Stock adjustment CSV

Required columns:

```csv
item_code,holder_code,operation,quantity,reason,note
I-0001,C-0042,remove,20,use,prototype build
I-0002,C-0042,add,500,purchase,new delivery
```

Rules:

- `operation`: `add` or `remove`;
- `quantity`: positive number;
- `reason`: `purchase`, `use`, `transfer`, or `other`;
- the referenced `Stock` row must already exist;
- the resulting quantity must not become negative.

### Inventory-count CSV

```csv
item_code,holder_code,counted_quantity,note
I-0001,C-0042,277,physical count
```

`counted_quantity` is an absolute non-negative physical count. Preview shows the correction from the currently recorded quantity.

### Placement CSV

```csv
unit_code,zone_code,support_unit_code,order_key,note
C-0042,Z-0127,,100,cleanup
C-0072,,C-0042,100,stacked on box
```

Exactly one of `zone_code` or `support_unit_code` must be present.

The same single-parent, no-self-support, and no-cycle rules used by the GUI are enforced. `order_key` is an internal relative ordering value and defaults to 100 when omitted. A later human-friendly reordering GUI may remove the need to edit this value directly.

### Operation JSON

Machine-oriented mixed batches use schema `lab-inventory.operations.v1`.

```json
{
  "schema": "lab-inventory.operations.v1",
  "operations": [
    {
      "type": "stock_adjust",
      "item_code": "I-0001",
      "holder_code": "C-0042",
      "operation": "remove",
      "quantity": "20",
      "reason": "use",
      "note": "prototype build"
    },
    {
      "type": "move_unit",
      "unit_code": "C-0072",
      "zone_code": "Z-0201",
      "order_key": 100
    }
  ]
}
```

V1 supports `stock_adjust`, `stock_count`, and `move_unit` operations.

## V1 limits

- UTF-8 input;
- maximum file size: 1 MB;
- maximum operations per batch: 1000.

These are operational guardrails, not domain limits. Raise them only after representative workstation validation.

## Import safety pipeline

Every mutating import follows:

```text
upload
  -> parse
  -> schema validation
  -> semantic validation
  -> preview current -> resulting state
  -> explicit confirmation
  -> re-check preview preconditions
  -> one transactional commit
  -> audit records
```

A parse or validation error must not partially modify operational state.

## Stale-preview protection

Preview captures the current quantities/placements of every affected record as preconditions.

At confirmation, those preconditions are checked again inside the write transaction before mutations begin. If another user changed an affected stock or placement after preview, the batch is rejected and must be previewed again.

This prevents an old browser preview from silently overwriting newer operational state.

## Stock changes

Normal stock-change imports express operations rather than replacing a current-state spreadsheet.

Absolute quantities are reserved for the explicit inventory-count/reconciliation operation.

## Placement changes

Bulk placement imports identify the physical unit plus either a placement zone or supporting physical unit. The resulting support graph is validated as a whole, so cycles created only by the combination of several batch operations are also rejected.

## Snapshot export

Authenticated users can export `lab-inventory.snapshot.v1` JSON containing current rooms, fixtures, placement zones, catalog items, physical units, placements, and stock quantities.

The export:

- contains stable internal IDs and human-facing codes;
- includes a generation timestamp;
- is a read-only reconciliation/interchange snapshot;
- is **not** the database backup mechanism;
- is not blindly re-importable as an authoritative replacement.

Operational disaster recovery uses the database-aware SQLite backup/restore procedure instead.

## Formats intentionally deferred

XLSX and YAML remain valid future interfaces, but are not required for V1. Add them when a concrete workflow benefits enough to justify the additional parser dependency and test surface. CSV covers human-edited tabular operations; JSON covers machine-oriented structured batches without adding dependencies.
