# Inventory master-data management

This procedure is for the `Maintainer` role. Routine CatalogItem and PhysicalUnit management does not require Django Admin, source-code edits, or SQL.

## Open Master

Use `Master` in the application header.

The page contains two independent concepts:

- `CatalogItem`: the type/model/category being tracked;
- `PhysicalUnit`: an individually identifiable physical object such as a reusable container, cardboard carton, power supply, soldering iron, or tool.

Do not merge these concepts merely because a physical unit has a known product model.

## Add a quantity-tracked item

Examples include screws, nuts, filament mass, wire length, and connector counts.

1. Select `品目を追加`.
2. Assign a durable Item ID such as `I-0042`.
3. Select `数量管理`.
4. Enter the unit (`pcs`, `g`, `m`, etc.).
5. Optionally enter a minimum-stock threshold.
6. Save.

Actual stock quantities are not edited on this form. Add the item to a holder/container and use normal audited stock operations.

## Add an individually tracked item type

For a product/model whose individual units are tracked separately:

1. create a CatalogItem with `個体管理`;
2. create one PhysicalUnit per tracked physical instance;
3. optionally associate each PhysicalUnit with that CatalogItem.

Physical placement is still recorded on the PhysicalUnit, not the CatalogItem.

## Add a container/tool/equipment unit

Select `箱・工具・機器を追加`.

Record:

- durable Unit ID;
- human-readable name;
- physical kind;
- optional CatalogItem/model association;
- approximate dimensions when known.

Dimensions are optional. Missing dimensions do not prevent use; the 3D view uses a clearly identified placeholder size.

After creation, set the normal storage position using the standard `位置を変更` workflow.

## Stable IDs

Existing Item IDs and Unit IDs are disabled in the normal edit forms. A rename changes descriptive text, not durable identity.

This keeps:

- printed labels valid;
- QR detail routes stable;
- audit records understandable;
- exports reconcilable.

## Tracking-mode stability

Once a CatalogItem has stock rows or associated PhysicalUnits, the normal Maintainer form no longer permits changing its tracking mode between quantity and individual tracking.

Changing that semantic after operational data exists would change the meaning of historical records. If a genuine migration is required, treat it as an application/data migration and document it explicitly.

## Retirement

Do not delete a master-data entity during normal operation. Clear `使用中` instead.

Inactive entities remain available to historical relationships and audit records but are excluded from new normal selections where appropriate.
