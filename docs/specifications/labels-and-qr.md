# Physical labels and QR codes

## Purpose

Physical labels connect the operational application to shelves, containers, tools, and equipment without making printed text a second source of truth.

## Primary identity

The durable human-facing code is the primary printed identity, for example:

```text
Z-0127
C-0042
A-0017
```

A label identifies the physical zone or physical unit. It does not identify the current contents of a reusable container.

## QR payload

The QR code contains the absolute stable application URL for the labeled entity:

```text
https://inventory.example/u/C-0042/
https://inventory.example/z/Z-0127/
```

Scanning the code opens the normal authenticated detail route. If the scanner is not logged in, normal authentication occurs first.

The QR payload must not contain:

- current stock quantity;
- current rack/shelf assignment of a movable unit;
- current container contents;
- 3D coordinates;
- mutable descriptive metadata.

## Printed descriptive text

V1 label sheets print:

- durable code;
- short current name;
- entity/category label;
- QR code.

The durable code is authoritative identity. The descriptive name is convenience text and may become stale after a rename; the QR detail page remains authoritative.

## Production-domain rule

QR labels should be printed only from the long-lived production custom domain. Labels printed from `localhost`, a workstation IP address, or a temporary tunnel hostname are not suitable for durable deployment.

The application displays a warning when a print sheet is generated from localhost.

## Label sizes

V1 browser-print presets are:

- 45 x 25 mm;
- 60 x 35 mm;
- 80 x 45 mm.

Browser print scaling should normally be 100%. A test print should be checked against the actual label stock before bulk printing.

These presets are presentation settings, not domain data. Additional printer-specific templates may be added without changing identifier semantics.

## Generation

QR SVGs are generated server-side from the current request origin and stable detail route. The application uses SVG to avoid raster-resolution requirements and does not depend on an external QR-generation service.
