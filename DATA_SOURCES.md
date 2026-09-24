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

Planned fields:
- supermarket and convenience-store locations
- brand/name tags
- public-transport stations and stops
- Baku administrative boundary

OpenStreetMap coverage is community maintained, so competitor counts will be treated as a coverage signal rather than a complete census of every shop.

## Population and residential demand

Preferred official source:
- State Statistical Committee of the Republic of Azerbaijan
- https://www.stat.gov.az/source/demoqraphy/?lang=en

The official statistics provide population by administrative territorial unit. If the project needs finer spatial resolution than district-level population allows, a gridded population source will be added and documented separately.

## Principle

Every feature used in the final expansion score should have:
1. a documented source,
2. a clear business interpretation,
3. a known limitation.
