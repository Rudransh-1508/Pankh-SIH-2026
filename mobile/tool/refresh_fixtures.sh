#!/bin/bash
# Refresh the API responses the app's tests run against, from a local API on port 8000.
# Usage (from mobile/): tool/refresh_fixtures.sh
set -euo pipefail
API=${PANKH_API_URL:-http://localhost:8000}/v1
OUT=$(dirname "$0")/../test/fixtures
curl -sf "$API/facts/schema" > "$OUT/fact_schema.json"
curl -sf -X POST "$API/eligibility?academic_year=2026" -H 'content-type: application/json' \
  -d '{"facts": {}}' > "$OUT/eligibility_empty.json"
curl -sf -X POST "$API/eligibility?academic_year=2026" -H 'content-type: application/json' \
  -d '{"facts": {"is_scheduled_tribe": true, "education_level": "undergraduate", "studies_abroad": false, "institution_recognised": true, "family_income": 240000, "repeating_stage_in_other_subject": false, "admitted_to_top_class_institute": false, "current_mota_award": "none", "holds_other_scholarship": false}}' \
  > "$OUT/eligibility_post_matric.json"
curl -sf -X POST "$API/eligibility?academic_year=2026" -H 'content-type: application/json' \
  -d '{"facts": {"is_scheduled_tribe": true}}' > "$OUT/eligibility_st.json"
echo "Fixtures refreshed in $OUT"
