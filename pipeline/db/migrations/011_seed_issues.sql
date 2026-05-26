INSERT INTO issues (issue_code, issue_name_en, issue_name_hi, category, icon) VALUES
  ('water',        'Water Supply',          'पानी / जल आपूर्ति',      'infrastructure', '💧'),
  ('roads',        'Roads & Connectivity',  'सड़क / कनेक्टिविटी',    'infrastructure', '🛣️'),
  ('electricity',  'Electricity',           'बिजली',                  'infrastructure', '⚡'),
  ('housing',      'Housing / PMAY',        'आवास / पीएमएवाई',        'infrastructure', '🏠'),
  ('jobs',         'Employment / Jobs',     'रोजगार / नौकरी',         'economy',        '💼'),
  ('price_rise',   'Price Rise / Inflation','महंगाई',                 'economy',        '📈'),
  ('farmer',       'Farmer Issues',         'किसान समस्याएं',         'economy',        '🌾'),
  ('sugarcane',    'Sugarcane / Sugar Mill','गन्ना / चीनी मिल',       'economy',        '🎋'),
  ('women_safety', 'Women Safety',          'महिला सुरक्षा',          'social',         '🛡️'),
  ('health',       'Health & Hospitals',    'स्वास्थ्य / अस्पताल',   'social',         '🏥'),
  ('education',    'Education / Schools',   'शिक्षा / स्कूल',         'social',         '📚'),
  ('corruption',   'Corruption',            'भ्रष्टाचार',             'governance',     '⚖️'),
  ('law_order',    'Law & Order',           'कानून व्यवस्था',         'governance',     '🚔'),
  ('governance',   'Panchayat Governance',  'पंचायत शासन',            'governance',     '🏛️'),
  ('other',        'Other',                 'अन्य',                   'other',          '❓')
ON CONFLICT (issue_code) DO NOTHING;
