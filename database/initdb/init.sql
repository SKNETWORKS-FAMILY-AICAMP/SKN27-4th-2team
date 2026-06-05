-- Create vector extension if needed later
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Core breeds table
CREATE TABLE IF NOT EXISTS breeds (
    id BIGSERIAL PRIMARY KEY,
    breed_name VARCHAR(150) UNIQUE NOT NULL,
    dogapi_id INTEGER,
    breed_group VARCHAR(100),
    life_span VARCHAR(100),
    temperament TEXT,
    origin VARCHAR(150),
    weight_metric VARCHAR(100),
    height_metric VARCHAR(100),
    image_url TEXT,
    height_min NUMERIC(5,2),
    height_max NUMERIC(5,2),
    weight_min NUMERIC(5,2),
    weight_max NUMERIC(5,2),
    life_expectancy_min NUMERIC(4,2),
    life_expectancy_max NUMERIC(4,2),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Scores table
CREATE TABLE IF NOT EXISTS breed_scores (
    breed_id BIGINT PRIMARY KEY REFERENCES breeds(id) ON DELETE CASCADE,
    affectionate_with_family_score INTEGER CHECK (affectionate_with_family_score BETWEEN 1 AND 5),
    good_with_young_children_score INTEGER CHECK (good_with_young_children_score BETWEEN 1 AND 5),
    good_with_other_dogs_score INTEGER CHECK (good_with_other_dogs_score BETWEEN 1 AND 5),
    shedding_level_score INTEGER CHECK (shedding_level_score BETWEEN 1 AND 5),
    coat_grooming_frequency_score INTEGER CHECK (coat_grooming_frequency_score BETWEEN 1 AND 5),
    drooling_level_score INTEGER CHECK (drooling_level_score BETWEEN 1 AND 5),
    openness_to_strangers_score INTEGER CHECK (openness_to_strangers_score BETWEEN 1 AND 5),
    playfulness_level_score INTEGER CHECK (playfulness_level_score BETWEEN 1 AND 5),
    watchdog_protective_nature_score INTEGER CHECK (watchdog_protective_nature_score BETWEEN 1 AND 5),
    adaptability_level_score INTEGER CHECK (adaptability_level_score BETWEEN 1 AND 5),
    trainability_level_score INTEGER CHECK (trainability_level_score BETWEEN 1 AND 5),
    energy_level_score INTEGER CHECK (energy_level_score BETWEEN 1 AND 5),
    barking_level_score INTEGER CHECK (barking_level_score BETWEEN 1 AND 5),
    mental_stimulation_needs_score INTEGER CHECK (mental_stimulation_needs_score BETWEEN 1 AND 5)
);

-- 3. Attributes array table
CREATE TABLE IF NOT EXISTS breed_attributes (
    breed_id BIGINT PRIMARY KEY REFERENCES breeds(id) ON DELETE CASCADE,
    coat_type_array TEXT[],
    coat_length_array TEXT[],
    colors_array TEXT[],
    markings_array TEXT[]
);
