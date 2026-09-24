-- Candidate-zone review
-- Run after src/analyze_screen_diagnostics.py has generated
-- data/processed/candidate_zone_profiles.csv.

create or replace view candidate_zones as
select *
from read_csv_auto('data/processed/candidate_zones.csv', header = true);

create or replace view zone_profiles as
select *
from read_csv_auto('data/processed/candidate_zone_profiles.csv', header = true);

-- Put the shortlist into a business-review table.
select
    z.screening_rank,
    z.district,
    z.candidate_cells,
    round(z.mean_nearest_bravo_km, 2) as mean_nearest_bravo_km,
    round(z.population_density_per_sq_km, 0) as population_density_per_sq_km,
    round(z.mean_competitor_count_1_5km, 1) as competitors_within_1_5km,
    round(z.mean_transit_count_1km, 1) as transit_features_within_1km,
    round(p.bravo_gap_percentile, 0) as bravo_gap_percentile,
    round(p.population_density_percentile, 0) as population_density_percentile,
    round(p.food_retail_activity_percentile, 0) as food_retail_activity_percentile,
    round(p.transit_percentile, 0) as transit_percentile
from candidate_zones z
left join zone_profiles p
    using (screening_rank, district)
order by z.screening_rank;

-- Find candidates whose evidence is balanced rather than being driven by
-- one unusually strong public-data signal.
select
    z.screening_rank,
    z.district,
    least(
        p.bravo_gap_percentile,
        p.population_density_percentile,
        p.food_retail_activity_percentile
    ) as weakest_core_signal_percentile,
    greatest(
        p.bravo_gap_percentile,
        p.population_density_percentile,
        p.food_retail_activity_percentile
    ) as strongest_core_signal_percentile
from candidate_zones z
join zone_profiles p
    using (screening_rank, district)
order by weakest_core_signal_percentile desc, z.screening_rank;
