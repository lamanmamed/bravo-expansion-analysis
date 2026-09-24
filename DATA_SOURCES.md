# Data sources

## Bravo store network

**Source:** Bravo Supermarket official store page  
**URL:** https://www.bravosupermarket.az/en/branches/

Fields used:
- store name
- store format
- address
- opening hours
- Google Maps destination coordinates

The store page is treated as the primary source for Bravo locations.

## Other supermarkets and transport

**Source:** OpenStreetMap

Fields currently collected:
- supermarket and convenience-store locations
- brand/name tags
- public-transport stations and stops
- Baku administrative boundary

OpenStreetMap coverage is community maintained, so competitor counts will be treated as a coverage signal rather than a complete census of every shop.

## Population and residential demand

**Source:** State Statistical Committee of the Republic of Azerbaijan  
**Table:** Area, population size and population density of the economic regions and administrative territorial units of the Republic of Azerbaijan  
**Reference date:** 01.01.2026  
**URL:** https://www.stat.gov.az/source/demoqraphy/en/001_15en.xls

The project extracts Baku total plus the 12 administrative districts from the official workbook. District-level density is a broad demand signal, not a street-level population estimate.

## Principle

Every feature used in the final expansion score should have:
1. a documented source,
2. a clear business interpretation,
3. a known limitation.