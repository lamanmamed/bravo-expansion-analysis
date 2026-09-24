-- Candidate-area screening queries
-- These views use the generated CSV outputs from src/build_expansion_screen.py.

create or replace view expansion_cells as
select *
from read_csv_auto('data/processed/expansion_screen_cells.csv', header = true);

create or replace view candidate_zones as
select *
from read_csv_auto('data/processed/candidate_zones.csv', header = true);

-- Business-facing shortlist.
select
    screening_rank,
    district,
    candidate_cells,
    round(mean_nearest_bravo_km, 2) as mean_nearest_bravo_km,
    round(population_density_per_sq_km, 0) as population_density_per_sq_km,
    round(mean_competitor_count_1_5km, 1) as competitors_within_1_5km,
    round(mean_transit_count_1km, 1) as transit_features_within_1km,
    round(max_screen_score, 3) as max_screen_score
from candidate_zones
order by screening_rank
limit 10;

-- How many genuine coverage gaps exist by district?
select
    district,
    count(*) filter (where eligible_gap = true) as eligible_gap_cells,
    round(avg(nearest_bravo_km) filter (where eligible_gap = true), 2)
        as avg_nearest_bravo_km,
    round(avg(context_fit_score) filter (where eligible_gap = true), 3)
        as avg_context_fit_score
from expansion_cells
where district is not null
group by district
order by eligible_gap_cells desc, district;

-- Cells that are stable under the sensitivity analysis.
select
    cell_id,
    district,
    round(nearest_bravo_km, 2) as nearest_bravo_km,
    competitor_count_1_5km,
    transit_count_1km,
    round(density_per_sq_km, 0) as density_per_sq_km,
    robust_top15_hits,
    round(average_sensitivity_rank, 1) as average_sensitivity_rank
from expansion_cells
where robust_top15_hits >= 2
order by robust_top15_hits desc, average_sensitivity_rank;
