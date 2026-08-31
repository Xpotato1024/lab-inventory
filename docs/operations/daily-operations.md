# Daily operations

This document describes the browser-first routine workflow. It deliberately uses laboratory concepts rather than database terminology.

## Find an item

1. Sign in.
2. Enter a name, part number, item code, physical-unit code, or placement-zone code in the search box.
3. Open the matching item, box/equipment/tool, or storage location.
4. Use the displayed normal storage position to locate the object.
5. Choose **3Dで表示** when spatial context is helpful.

The 3D view is generated from the same SoT data. It is a locator aid, not a second authoritative model.

## Check low stock

The home page reports the number of quantity-tracked items below their configured minimum-stock threshold.

Choose **一覧を見る** to inspect:

- current aggregate quantity across all holders;
- minimum-stock target;
- exact shortage amount;
- holders/containers where current stock is recorded.

Items without a minimum-stock threshold are intentionally excluded from this warning list.

## Record stock use or arrival

From a physical-unit detail page:

1. Find the relevant stock row.
2. Choose **増減**.
3. Select whether stock is being added or reduced.
4. Enter a positive quantity and reason.
5. Confirm.

The operator never enters a signed database delta directly. The application calculates the sign and creates a `StockChange` audit record in the same transaction as the quantity update.

The operation is rejected if it would make quantity negative.

## Perform an inventory count

Use **棚卸** when the physical count is authoritative.

1. Open the stock row from the physical-unit page.
2. Choose **棚卸**.
3. Enter the absolute quantity physically counted.
4. Confirm.

The application records the difference between the former quantity and the counted quantity as an inventory-count correction.

Do not use a stale spreadsheet to overwrite current quantities without an explicit validated inventory-count workflow.

## Change normal storage position

Use **位置を変更** when the normal place an object is returned to has changed.

Choose one of:

- **棚・机・壁面などへ置く** — place the unit directly in/on a `PlacementZone`;
- **別の物の上へ置く** — stack the unit on another physical unit.

Temporary movement while actively using a tool does not normally require an update.

## Left-to-right order

A shelf has no fixed number of slots. The normal GUI uses relative choices:

- leftmost;
- rightmost;
- immediately before a selected unit;
- immediately after a selected unit.

The application converts that choice to its internal mutable ordering and normalizes sibling order automatically.

The UI derives labels such as:

```text
左から1番目
左から2番目
左から3番目
```

The displayed ordinal is not an identifier. Inserting another object changes later ordinals without changing object identity or printed labels.

## Stacked objects

If `C-002` is placed on `C-001`, and `C-001` is placed on `Z-010`, then `C-002` has the same effective root placement zone `Z-010`.

Moving the root unit changes the effective location of everything stacked above it without rewriting every descendant placement record.

The application rejects self-support and support cycles. The 3D view renders the same recursive relationship rather than maintaining a separate stack model.

## Add a newly tracked stock item to a holder

From a physical-unit detail page choose **品目を追加**.

Select a quantity-tracked catalog item and enter the physical current quantity. The initial quantity is recorded as an initial inventory-count audit event.

Creating/editing CatalogItems and PhysicalUnits is handled through the Maintainer **Master** UI. Room/fixture/zone maintenance is handled through **Layout**.
