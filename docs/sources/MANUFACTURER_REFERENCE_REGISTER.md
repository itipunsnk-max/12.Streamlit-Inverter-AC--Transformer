# Manufacturer reference register

This file records the public manufacturer pages used to update the Draft reference
release. It stores factual field extracts and links only; manufacturer PDFs and
images are not redistributed by this repository.

## Sungrow inverter references

| Models | Official document | Version/date | Fields used |
|---|---|---|---|
| SG36CX-P2, SG40CX-P2, SG50CX-P2 | https://info-support.sungrowpower.com/application/pdf/2023/12/21/DS_20231219_SG36_40_50CX-P2_Datasheet_V4_EN.pdf | Datasheet V4, 2023-12-19 | DC limits, MPPT count, rated/max AC power and current, 400 V rating, 3-N-PE connection |
| SG125CX-P2 | https://info-support.sungrowpower.com/application/pdf/2023/06/25/DS_20230615_SG125CX-P2_Datasheet_V14_EN.pdf | Datasheet V14, 2023-06-15 | DC limits, MPPT count, rated/max AC power and current, 400/415 V ratings, 3-N-PE connection |
| SG150CX | https://info-support.sungrowpower.com/application/pdf/2025/08/13/DS_20250806_SG150CX_Datasheet_V7_EN.pdf | Datasheet V7, 2025-08-06 | DC limits, MPPT count, rated/max AC power and current at 400 V, 3-N-PE connection |
| SG350HX-20 | https://info-support.sungrowpower.com/application/pdf/2025/01/10/DS_202401218_SG350HX-20_Datasheet_V7_EN.pdf | Datasheet V7, 2024-12-18 | 320 kW rated condition at 40 C and 800 V, 352 kVA at 30 C, DC limits, 254 A maximum AC current, 3-PE connection |

The SG350HX-20 row intentionally separates rated-condition active power
(`320 kW` at 40 C) from the datasheet's temperature-dependent apparent-power
entry (`352 kVA` at 30 C). No recommended maximum PV input power or DC/AC ratio
is inferred for this model.

## Phelps Dodge cable references

| Cable family | Official page | Fields used |
|---|---|---|
| CV / CV-FD single-core | https://www.pdcable.com/en/product-en/building-and-construction/cv-fd-1-2/ | Copper conductor, XLPE insulation, 0.6/1 kV rating, installation applicability |
| 60227 IEC 01 (THW) | https://www.pdcable.com/en/product-en/60227-iec-01-thw-1-2/ | Copper conductor, PVC/C insulation, 450/750 V rating, 70 C maximum conductor temperature |
| 60227 IEC 01 (THW) dimensions | https://www.pdcable.com/wp-content/uploads/2019/09/Phelps-Dodge_Building-Wires-1.pdf | Published maximum outside diameters for the Ground cable rows |

CV/CV-FD outside diameters in the Draft release remain workbook transcriptions.
THW outside diameters use the published maximum values from the linked brochure.
Conduit internal diameters remain screening values. CV/CV-FD OD and conduit ID
require current manufacturer confirmation before construction issue.

## Use boundary

Manufacturer data supports equipment identity and nameplate limits only. Cable
ampacity tables, correction factors, protective-earth sizing, conduit fill, utility
requirements, short-circuit withstand, voltage drop, grouping, and installation
approval retain their own source and verification status.
