"""Record Links between registers that describe the same people differently.

Education registers (UDISE+) and scholarship registrations (NSP) share no identifier Pankh
may use: joining on Aadhaar numbers is not allowed for this purpose. People are matched
probabilistically instead, with Splink, on names reduced to Indic-aware sound-alike keys,
date of birth and gender, within the same district. Every Record Link keeps the weight each
field contributed, so a Reviewer can see why two records were judged the same person.
"""

import logging
import re
from dataclasses import dataclass

import splink.comparison_level_library as cll
import splink.comparison_library as cl
from splink import Linker, SettingsCreator, block_on
from splink.backends.duckdb import DuckDBAPI

from app.verification.names import name_key

LINK_THRESHOLD = 0.9
POSSIBLE_THRESHOLD = 0.5
_FIELDS = ("name", "date_of_birth", "gender")

logging.getLogger("splink").setLevel(logging.WARNING)

# One comparison with mutually exclusive levels: two comparisons of the same names would count
# the same evidence twice. Names arrive as sound-alike keys, so shared words are compared
# first, then the whole name fuzzily for spellings the keys do not reconcile (Lakra, Lakda).
_NAME_COMPARISON = cl.CustomComparison(
    comparison_levels=[
        cll.NullLevel("name_tokens"),
        cll.ArrayIntersectLevel("name_tokens", min_intersection=2),
        cll.JaroWinklerLevel("name_sorted", 0.9),
        cll.ArrayIntersectLevel("name_tokens", min_intersection=1),
        cll.ElseLevel(),
    ],
    output_column_name="name",
    comparison_description="Name words, then whole name",
)


@dataclass(frozen=True)
class PersonRecord:
    id: str
    name: str
    date_of_birth: str
    gender: str | None
    district: str
    state: str


@dataclass(frozen=True)
class RecordLink:
    left_id: str
    right_id: str
    probability: float
    weights: dict[str, float]
    """Match weight (log2 Bayes factor) each field contributed; positive supports a match."""

    @property
    def is_link(self) -> bool:
        return self.probability >= LINK_THRESHOLD


def _skeleton(key: str) -> str:
    """Drop every 'a' after the first letter. Whether a short 'a' is written varies with
    script and language (Basumatary, बसुमतारी), so it is ignored when linking registers."""
    return key[:1] + re.sub("a", "", key[1:])


def _row(record: PersonRecord) -> dict:
    tokens = sorted({_skeleton(key) for key in name_key(record.name)})
    return {
        "unique_id": record.id,
        "name_tokens": tokens or None,
        "name_sorted": " ".join(tokens) or None,
        "date_of_birth": record.date_of_birth,
        "gender": record.gender,
        "district": f"{record.state}/{record.district}".lower(),
    }


def link(left: list[PersonRecord], right: list[PersonRecord]) -> list[RecordLink]:
    """The best match on the right for each left record that has one worth reporting."""
    if not left or not right:
        return []
    db = DuckDBAPI()
    settings = SettingsCreator(
        link_type="link_only",
        comparisons=[
            _NAME_COMPARISON,
            cl.DateOfBirthComparison(
                "date_of_birth",
                input_is_string=True,
                datetime_thresholds=[1, 1],
                datetime_metrics=["month", "year"],
            ),
            cl.ExactMatch("gender"),
        ],
        blocking_rules_to_generate_predictions=[
            block_on("district"),
            block_on("date_of_birth"),
        ],
        retain_intermediate_calculation_columns=True,
    )
    linker = Linker(
        [
            db.register([_row(r) for r in left], table_name="left_records"),
            db.register([_row(r) for r in right], table_name="right_records"),
        ],
        settings,
        log_level=logging.WARNING,
    )
    linker.training.estimate_probability_two_random_records_match(
        [block_on("name_sorted", "date_of_birth")], recall=0.7
    )
    linker.training.estimate_u_using_random_sampling(max_pairs=2e5)
    # Each training pass blocks on one field so the others' weights can be learned: blocking
    # on names teaches how much a disagreeing date of birth counts against a match.
    training = linker.training
    training.estimate_parameters_using_expectation_maximisation(block_on("name_sorted", "district"))
    training.estimate_parameters_using_expectation_maximisation(block_on("date_of_birth"))
    predictions = linker.inference.predict(threshold_match_probability=POSSIBLE_THRESHOLD)

    best: dict[str, RecordLink] = {}
    for row in predictions.as_record_list():
        weights = {
            field: round(row[f"mw_{field}"], 2)
            for field in _FIELDS
            if row.get(f"mw_{field}") is not None
        }
        candidate = RecordLink(
            left_id=row["unique_id_l"],
            right_id=row["unique_id_r"],
            probability=round(row["match_probability"], 4),
            weights=weights,
        )
        current = best.get(candidate.left_id)
        if current is None or candidate.probability > current.probability:
            best[candidate.left_id] = candidate
    return list(best.values())
