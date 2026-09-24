-- Phase 1 network summary
-- Run with DuckDB after collecting data/raw/bravo_stores.csv.

create or replace view bravo_stores as
select *
from read_csv_auto('data/raw/bravo_stores.csv', header = true);

-- How is the Baku network split by format?
select
    store_format,
    count(*) as store_count,
    round(100.0 * count(*) / sum(count(*)) over (), 1) as share_pct
from bravo_stores
where in_baku_study_bbox = true
group by store_format
order by store_count desc;

-- Which records need manual data-quality review?
select
    store_name,
    store_format,
    address,
    latitude,
    longitude
from bravo_stores
where address is null
   or latitude is null
   or longitude is null
order by store_name;

-- Overall first-pass network size.
select
    count(*) as all_official_locations,
    count(*) filter (where in_baku_study_bbox = true) as locations_in_initial_baku_bbox,
    count(distinct store_format) filter (where in_baku_study_bbox = true) as formats_in_baku
from bravo_stores;
