-- Add geocoded_at timestamp for booth_master used by geocode_booths.py
ALTER TABLE booth_master
    ADD COLUMN IF NOT EXISTS geocoded_at TIMESTAMPTZ;

-- Optional: index to speed up geocoded/non-geocoded queries
CREATE INDEX IF NOT EXISTS idx_booth_geocoded_at ON booth_master(geocoded_at);
