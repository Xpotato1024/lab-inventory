# Structured import and export

## Role

Structured files are secondary operational interfaces. They do not replace the operational datastore as the source of truth.

## Preferred formats

- CSV/XLSX: human-edited bulk tabular records such as catalog items, containers, and inventory-count sheets.
- YAML: hierarchical layout/configuration data where nested structure materially improves readability.
- JSON: machine-oriented interchange and explicit batches of operations.

## Import safety pipeline

Every mutating import must follow this sequence:

```text
upload
  -> parse
  -> schema validation
  -> semantic validation
  -> preview diff/operations
  -> explicit confirmation
  -> transactional commit
  -> audit records
```

A parse or validation error must not partially modify operational state.

## Stock changes

Normal stock-change imports should express operations rather than blindly replacing a current-state spreadsheet.

Example:

```csv
item_code,container_code,operation,quantity,reason
I-0001,C-0042,remove,20,use
I-0002,C-0042,add,500,purchase
```

Absolute counted quantities are reserved for explicit inventory-count/reconciliation workflows. The system should present the difference between recorded and counted quantity before committing the adjustment.

## Placement changes

Bulk placement imports should identify the physical unit plus either a placement zone or supporting physical unit, together with optional relative ordering.

A placement import must enforce the same no-cycle and single-current-placement invariants as the GUI.

## Export

Exports should include stable entity identifiers/codes sufficient for later reconciliation. Exported files are snapshots and must be clearly timestamped where ambiguity is possible.

Re-importing an old export must never silently overwrite newer operational state without an explicit reconciliation workflow.
