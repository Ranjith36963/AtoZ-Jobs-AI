-- Tier 1: Reference data (committed to git)
-- See PLAYBOOK.md §1.8 and SPEC.md §1.6

-- =============================================================================
-- Sources (4 API sources)
-- =============================================================================
INSERT INTO sources (name, api_base_url, is_active) VALUES
    ('reed',      'https://www.reed.co.uk/api/1.0',       true),
    ('adzuna',    'https://api.adzuna.com/v1/api/jobs/gb', true),
    ('jooble',    'https://jooble.org/api',                true),
    ('careerjet', 'https://search.api.careerjet.net/v4',   true);

-- =============================================================================
-- Internal Categories (11 categories — SPEC.md §3.5)
-- These are enforced in Python code (processing/category.py), not a DB table.
-- Listed here as reference for the category mapping:
--   1. Technology
--   2. Finance
--   3. Healthcare
--   4. Engineering
--   5. Education
--   6. Sales & Marketing
--   7. Legal
--   8. Construction
--   9. Creative & Media
--  10. Hospitality
--  11. Other
-- =============================================================================

-- =============================================================================
-- UK Cities (~100 major cities with coordinates for geocoding fallback)
-- See SPEC.md §3.4: "Pre-populated table of ~100 UK cities with coordinates"
-- =============================================================================
INSERT INTO uk_cities (name, region, latitude, longitude, population) VALUES
    -- England — London
    ('London',              'Greater London',         51.5074, -0.1278, 8982000),
    ('Central London',      'Greater London',         51.5155, -0.0922, NULL),
    ('City of London',      'Greater London',         51.5155, -0.0922, NULL),

    -- England — South East
    ('Brighton',            'South East England',     50.8225, -0.1372, 229700),
    ('Southampton',         'South East England',     50.9097, -1.4044, 252796),
    ('Portsmouth',          'South East England',     50.8198, -1.0880, 238137),
    ('Reading',             'South East England',     51.4543, -0.9781, 174224),
    ('Oxford',              'South East England',     51.7520, -1.2577, 152450),
    ('Milton Keynes',       'South East England',     52.0406, -0.7594, 248821),
    ('Guildford',           'South East England',     51.2362, -0.5704, 77057),
    ('Canterbury',          'South East England',     51.2802, 1.0789,  55240),
    ('Slough',              'South East England',     51.5105, -0.5950, 164000),
    ('Crawley',             'South East England',     51.1092, -0.1872, 118550),
    ('Basingstoke',         'South East England',     51.2667, -1.0876, 113776),

    -- England — South West
    ('Bristol',             'South West England',     51.4545, -2.5879, 467099),
    ('Bath',                'South West England',     51.3811, -2.3590, 94782),
    ('Exeter',              'South West England',     50.7184, -3.5339, 130428),
    ('Plymouth',            'South West England',     50.3755, -4.1427, 264200),
    ('Bournemouth',         'South West England',     50.7192, -1.8808, 187503),
    ('Swindon',             'South West England',     51.5558, -1.7797, 185609),
    ('Cheltenham',          'South West England',     51.8994, -2.0783, 118000),
    ('Gloucester',          'South West England',     51.8642, -2.2382, 129128),

    -- England — West Midlands
    ('Birmingham',          'West Midlands',          52.4862, -1.8904, 1141816),
    ('Coventry',            'West Midlands',          52.4068, -1.5197, 379387),
    ('Wolverhampton',       'West Midlands',          52.5870, -2.1288, 254406),
    ('Stoke-on-Trent',      'West Midlands',          53.0027, -2.1794, 256375),
    ('Worcester',           'West Midlands',          52.1936, -2.2216, 101659),
    ('Solihull',            'West Midlands',          52.4130, -1.7743, 214909),
    ('Walsall',             'West Midlands',          52.5860, -1.9827, 283378),

    -- England — East Midlands
    ('Nottingham',          'East Midlands',          52.9548, -1.1581, 321500),
    ('Leicester',           'East Midlands',          52.6369, -1.1398, 368600),
    ('Derby',               'East Midlands',          52.9225, -1.4746, 257174),
    ('Northampton',         'East Midlands',          52.2405, -0.9027, 224610),
    ('Lincoln',             'East Midlands',          53.2307, -0.5406, 103886),

    -- England — East of England
    ('Cambridge',           'East of England',        52.2053, 0.1218,  145818),
    ('Norwich',             'East of England',        52.6309, 1.2974,  213166),
    ('Ipswich',             'East of England',        52.0567, 1.1482,  138718),
    ('Luton',               'East of England',        51.8787, -0.4200, 225300),
    ('Peterborough',        'East of England',        52.5695, -0.2405, 202110),
    ('Colchester',          'East of England',        51.8860, 0.8919,  122000),
    ('Chelmsford',          'East of England',        51.7356, 0.4685,  178388),
    ('Southend-on-Sea',     'East of England',        51.5459, 0.7077,  183125),
    ('Watford',             'East of England',        51.6565, -0.3903, 96577),
    ('St Albans',           'East of England',        51.7553, -0.3360, 147373),

    -- England — North West
    ('Manchester',          'North West England',     53.4808, -2.2426, 553230),
    ('Liverpool',           'North West England',     53.4084, -2.9916, 496784),
    ('Preston',             'North West England',     53.7632, -2.7031, 141818),
    ('Blackpool',           'North West England',     53.8142, -3.0503, 139305),
    ('Bolton',              'North West England',     53.5785, -2.4299, 194189),
    ('Warrington',          'North West England',     53.3900, -2.5970, 209547),
    ('Chester',             'North West England',     53.1930, -2.8931, 118200),
    ('Blackburn',           'North West England',     53.7488, -2.4816, 117963),
    ('Lancaster',           'North West England',     54.0466, -2.8007, 52234),

    -- England — Yorkshire and the Humber
    ('Leeds',               'Yorkshire and the Humber', 53.8008, -1.5491, 503000),
    ('Sheffield',           'Yorkshire and the Humber', 53.3811, -1.4701, 584853),
    ('Bradford',            'Yorkshire and the Humber', 53.7960, -1.7594, 349561),
    ('Hull',                'Yorkshire and the Humber', 53.7457, -0.3367, 259778),
    ('York',                'Yorkshire and the Humber', 53.9591, -1.0815, 210618),
    ('Huddersfield',        'Yorkshire and the Humber', 53.6458, -1.7850, 162949),
    ('Doncaster',           'Yorkshire and the Humber', 53.5228, -1.1285, 311890),
    ('Wakefield',           'Yorkshire and the Humber', 53.6830, -1.4977, 99251),
    ('Rotherham',           'Yorkshire and the Humber', 53.4326, -1.3635, 264671),
    ('Harrogate',           'Yorkshire and the Humber', 53.9921, -1.5418, 160533),

    -- England — North East
    ('Newcastle upon Tyne', 'North East England',     54.9783, -1.6178, 302820),
    ('Sunderland',          'North East England',     54.9069, -1.3838, 277417),
    ('Middlesbrough',       'North East England',     54.5742, -1.2350, 140545),
    ('Durham',              'North East England',     54.7761, -1.5733, 48069),
    ('Darlington',          'North East England',     54.5235, -1.5527, 106000),

    -- Scotland
    ('Edinburgh',           'Scotland',               55.9533, -3.1883, 524930),
    ('Glasgow',             'Scotland',               55.8642, -4.2518, 635640),
    ('Aberdeen',            'Scotland',               57.1497, -2.0943, 196670),
    ('Dundee',              'Scotland',               56.4620, -2.9707, 148270),
    ('Inverness',           'Scotland',               57.4778, -4.2247, 63780),
    ('Stirling',            'Scotland',               56.1165, -3.9369, 37180),
    ('Perth',               'Scotland',               56.3950, -3.4308, 47430),

    -- Wales
    ('Cardiff',             'Wales',                  51.4816, -3.1791, 362756),
    ('Swansea',             'Wales',                  51.6214, -3.9436, 246563),
    ('Newport',             'Wales',                  51.5842, -2.9977, 154676),
    ('Wrexham',             'Wales',                  53.0469, -2.9930, 65692),
    ('Bangor',              'Wales',                  53.2274, -4.1293, 18808),

    -- Northern Ireland
    ('Belfast',             'Northern Ireland',       54.5973, -5.9301, 343542),
    ('Derry',               'Northern Ireland',       54.9966, -7.3086, 93512),
    ('Lisburn',             'Northern Ireland',       54.5162, -6.0580, 71465),
    ('Newry',               'Northern Ireland',       54.1751, -6.3402, 27433),

    -- Additional English cities
    ('Telford',             'West Midlands',          52.6766, -2.4469, 166641),
    ('Mansfield',           'East Midlands',          53.1472, -1.1987, 108841),
    ('Barnsley',            'Yorkshire and the Humber', 53.5526, -1.4797, 91297),
    ('Grimsby',             'Yorkshire and the Humber', 53.5675, -0.0800, 88243),
    ('Carlisle',            'North West England',     54.8951, -2.9382, 75306),
    ('Hereford',            'West Midlands',          52.0565, -2.7160, 61482),
    ('Salisbury',           'South West England',     51.0688, -1.7945, 45600),
    ('Truro',               'South West England',     50.2632, -5.0510, 21800),
    ('Taunton',             'South West England',     51.0150, -3.1002, 64621),
    ('Maidstone',           'South East England',     51.2722, 0.5227,  113137),
    ('Eastbourne',          'South East England',     50.7684, 0.2908,  103745),
    ('Hastings',            'South East England',     50.8540, 0.5730,  92855),
    ('Bedford',             'East of England',        52.1386, -0.4668, 106940),
    ('Stevenage',           'East of England',        51.9020, -0.2017, 87800),
    ('Stockport',           'North West England',     53.4106, -2.1575, 291775),
    ('Oldham',              'North West England',     53.5409, -2.1114, 237110),
    ('Rochdale',            'North West England',     53.6158, -2.1549, 222412);
