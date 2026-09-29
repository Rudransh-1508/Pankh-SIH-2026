"""A synthetic population of students, and how each register records them.

Everyone here is generated: no record describes a real person. The structure follows tribal
India (states, districts, Scheduled Tribes and their common surnames) so that matching,
verification and coverage behave as they would on real registers.

Registers disagree the way real ones do: names are transliterated differently, surnames go
missing, income certificates go stale and some records simply do not exist. Every person is
generated from a fixed seed, so the same person always has the same records.
"""

import hashlib
import random
from dataclasses import dataclass
from datetime import date, timedelta
from functools import cache, cached_property

SEED = 26238  # the problem statement's number
POPULATION_SIZE = 3000


@dataclass(frozen=True)
class Tribe:
    name: str
    name_hi: str
    surnames: tuple[tuple[str, str], ...]  # (Latin, Devanagari)
    pvtg: bool = False


def _t(name: str, name_hi: str, surnames: str, pvtg: bool = False) -> Tribe:
    pairs = tuple(tuple(pair.split("/")) for pair in surnames.split())
    return Tribe(name, name_hi, pairs, pvtg)  # type: ignore[arg-type]


SANTHAL = _t(
    "Santhal",
    "संथाल",
    "Murmu/मुर्मू Hansda/हांसदा Soren/सोरेन Tudu/टुडू Kisku/किस्कू Hembrom/हेम्ब्रम Marandi/मरांडी Baske/बास्के",
)
MUNDA = _t("Munda", "मुंडा", "Munda/मुंडा Purty/पूर्ति Kandulna/कंडुलना Bhengra/भेंगरा Topno/तोपनो")
ORAON = _t(
    "Oraon",
    "उरांव",
    "Tirkey/तिर्की Toppo/टोप्पो Kujur/कुजूर Lakra/लकड़ा Minz/मिंज Ekka/एक्का Kerketta/केरकेट्टा",
)
HO = _t("Ho", "हो", "Birua/बिरुवा Bodra/बोदरा Sinku/सिंकू Tiu/तियु Purty/पूर्ति")
GOND = _t(
    "Gond",
    "गोंड",
    "Netam/नेताम Markam/मरकाम Uikey/उइके Dhurve/धुर्वे Maravi/मरावी Kumre/कुमरे Poyam/पोयाम Mandavi/मंडावी",
)
BHIL = _t(
    "Bhil",
    "भील",
    "Bhuriya/भूरिया Damor/डामोर Vasava/वसावा Dindor/डिंडोर Katara/कटारा Kharadi/खराड़ी Ninama/निनामा",
)
KHOND = _t("Khond", "कंध", "Kanhar/कन्हार Majhi/माझी Mallick/मल्लिक Digal/डिगल")
MEENA = _t("Meena", "मीणा", "Meena/मीणा")
BODO = _t(
    "Bodo", "बोडो", "Basumatary/बसुमतारी Brahma/ब्रह्मा Narzary/नार्जारी Mushahary/मुशाहारी Boro/बोरो"
)
WARLI = _t("Warli", "वारली", "Bhoye/भोये Dumada/डुमाडा Valvi/वळवी Kharpade/खरपडे")
BAIGA = _t("Baiga", "बैगा", "Baiga/बैगा Dhurve/धुर्वे Maravi/मरावी", pvtg=True)
BIRHOR = _t("Birhor", "बिरहोर", "Birhor/बिरहोर", pvtg=True)
JUANG = _t("Juang", "जुआंग", "Juang/जुआंग Naik/नाइक", pvtg=True)


@dataclass(frozen=True)
class State:
    name: str
    code: str
    districts: tuple[str, ...]
    tribes: tuple[Tribe, ...]


STATES = (
    State(
        "Jharkhand",
        "JH",
        ("Ranchi", "Dumka", "Gumla", "West Singhbhum", "Khunti"),
        (SANTHAL, MUNDA, ORAON, HO, BIRHOR),
    ),
    State(
        "Odisha",
        "OD",
        ("Mayurbhanj", "Koraput", "Sundargarh", "Rayagada"),
        (SANTHAL, KHOND, MUNDA, GOND, JUANG),
    ),
    State("Chhattisgarh", "CG", ("Bastar", "Dantewada", "Surguja", "Kanker"), (GOND, ORAON)),
    State(
        "Madhya Pradesh",
        "MP",
        ("Jhabua", "Alirajpur", "Dindori", "Mandla", "Barwani"),
        (BHIL, GOND, BAIGA),
    ),
    State("Maharashtra", "MH", ("Nandurbar", "Gadchiroli", "Palghar"), (BHIL, GOND, WARLI)),
    State("Gujarat", "GJ", ("Dahod", "Narmada", "Tapi"), (BHIL,)),
    State("Rajasthan", "RJ", ("Banswara", "Dungarpur", "Udaipur"), (MEENA, BHIL)),
    State("Assam", "AS", ("Kokrajhar", "Udalguri", "Baksa"), (BODO,)),
    State("West Bengal", "WB", ("Jhargram", "Purulia"), (SANTHAL, ORAON)),
)

MALE_NAMES = (
    ("Birsa", "बिरसा"),
    ("Ramesh", "रमेश"),
    ("Sunil", "सुनील"),
    ("Mangal", "मंगल"),
    ("Somra", "सोमरा"),
    ("Budhu", "बुधु"),
    ("Suresh", "सुरेश"),
    ("Anil", "अनिल"),
    ("Rajesh", "राजेश"),
    ("Pradeep", "प्रदीप"),
    ("Vijay", "विजय"),
    ("Sanjay", "संजय"),
    ("Karan", "करण"),
    ("Rahul", "राहुल"),
    ("Manoj", "मनोज"),
    ("Dinesh", "दिनेश"),
    ("Lakhan", "लखन"),
    ("Sukra", "सुकरा"),
    ("Jitendra", "जितेंद्र"),
    ("Amit", "अमित"),
)
FEMALE_NAMES = (
    ("Sunita", "सुनीता"),
    ("Anita", "अनीता"),
    ("Sita", "सीता"),
    ("Phulmani", "फुलमनी"),
    ("Salge", "सलगे"),
    ("Rinki", "रिंकी"),
    ("Priyanka", "प्रियंका"),
    ("Mamta", "ममता"),
    ("Sushila", "सुशीला"),
    ("Kavita", "कविता"),
    ("Pooja", "पूजा"),
    ("Seema", "सीमा"),
    ("Basanti", "बसंती"),
    ("Lalita", "ललिता"),
    ("Reena", "रीना"),
    ("Sonam", "सोनम"),
    ("Jyoti", "ज्योति"),
    ("Menka", "मेनका"),
    ("Deepika", "दीपिका"),
    ("Sarita", "सरिता"),
)

# Spellings the same name commonly takes in different offices.
SPELLING_VARIANTS = {
    "Phulmani": ("Fulmani", "Phoolmani"),
    "Hansda": ("Hansdah", "Hasda"),
    "Tirkey": ("Tirkie", "Tirki"),
    "Murmu": ("Murmoo", "Marmu"),
    "Kerketta": ("Kerketa",),
    "Uikey": ("Uike", "Uikay"),
    "Pooja": ("Puja",),
    "Seema": ("Sima",),
    "Reena": ("Rina",),
    "Sunita": ("Sunitha",),
    "Anita": ("Aneeta",),
    "Jyoti": ("Jyothi", "Joti"),
    "Lakra": ("Lakda",),
    "Minz": ("Minj",),
    "Pradeep": ("Pradip",),
    "Dinesh": ("Dinesh Kumar",),
    "Rajesh": ("Rajesh Kumar",),
    "Kujur": ("Kujoor",),
    "Soren": ("Saren",),
    "Kisku": ("Kiskoo",),
    "Markam": ("Markaam",),
    "Vasava": ("Vasawa",),
    "Bhuriya": ("Bhuria",),
    "Basumatary": ("Basumatari",),
    "Meena": ("Mina",),
    "Netam": ("Netaam",),
}

EDUCATION_WEIGHTS = (
    ("class_9", 14),
    ("class_10", 12),
    ("class_11", 11),
    ("class_12", 10),
    ("diploma", 7),
    ("undergraduate", 26),
    ("postgraduate", 10),
    ("phd", 5),
    ("postdoc", 1),
)


@dataclass(frozen=True)
class Institution:
    code: str  # U-DISE code for schools, AISHE code for colleges and universities
    name: str
    kind: str  # school | college | university
    state: str
    district: str
    recognised: bool
    fellowship_eligible: bool  # UGC 2(f)/12(B), UGC-funded deemed, government-funded or INI
    management: str  # government | aided | private
    top_class_id: int | None = None  # serial number on the ministry's Top Class list


@dataclass(frozen=True)
class Person:
    id: str
    digilocker_id: str
    uid_token: str  # stands in for the Aadhaar number; registers share it, never the number itself
    uid_last4: str
    phone: str
    first_name: str
    first_name_hi: str
    surname: str
    surname_hi: str
    gender: str  # M | F
    date_of_birth: date
    state: State
    district: str
    tribe: Tribe | None  # None for the few non-ST people in the population
    family_income: int
    orphan: bool
    education_level: str
    institution: Institution | None
    abroad: bool
    bachelors_percent: float | None
    masters_percent: float | None
    net_roll_number: str | None
    net_result: str | None  # JRF | NET | None
    bank_seeded: bool
    disability_percent: int
    apaar_id: str
    has_caste_certificate: bool
    has_income_certificate: bool
    stale_income_certificate: bool
    caste_certificate_spelling: str  # the name as the caste certificate spells it
    enrolled_in_udise: bool
    has_scholarship_record: bool
    mota_award: str  # none | pre_matric | post_matric | top_class | nfst | nos

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.surname}"

    @property
    def name_hi(self) -> str:
        return f"{self.first_name_hi} {self.surname_hi}"

    @property
    def is_scheduled_tribe(self) -> bool:
        return self.tribe is not None

    def income_certificate(self, today: date | None = None) -> tuple[int, str, date]:
        """Amount, financial year and issue date of the Person's latest income certificate.

        A current certificate is for the financial year before the academic session; a stale
        one is two years older and shows the income as it was then.
        """
        today = today or date.today()
        session = today.year if today.month >= 4 else today.year - 1
        stale = self.stale_income_certificate
        start = session - (3 if stale else 1)
        amount = int(self.family_income * (0.8 if stale else 1))
        return amount, f"{start}-{(start + 1) % 100:02d}", date(start + 1, 5, 2)


@dataclass(frozen=True)
class Population:
    people: tuple[Person, ...]
    institutions: dict[str, Institution]

    def by_id(self, person_id: str) -> Person | None:
        return self._by("id").get(person_id)

    def by_digilocker_id(self, digilocker_id: str) -> Person | None:
        return self._by("digilocker_id").get(digilocker_id)

    def by_uid_token(self, uid_token: str) -> Person | None:
        return self._by("uid_token").get(uid_token)

    def by_net_roll_number(self, roll_number: str) -> Person | None:
        return self._by("net_roll_number").get(roll_number)

    def by_apaar_id(self, apaar_id: str) -> Person | None:
        return self._by("apaar_id").get(apaar_id)

    def by_phone(self, phone: str) -> Person | None:
        return self._by("phone").get(phone)

    def _by(self, attribute: str) -> dict[str, Person]:
        return self._indexes[attribute]

    @cached_property
    def _indexes(self) -> dict[str, dict[str, Person]]:
        attributes = ("id", "digilocker_id", "uid_token", "net_roll_number", "apaar_id", "phone")
        return {
            attribute: {getattr(p, attribute): p for p in self.people if getattr(p, attribute)}
            for attribute in attributes
        }


def _code(rng: random.Random, digits: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(digits))


def spelling(rng: random.Random, first: str, surname: str) -> str:
    """How another office might write this name."""
    roll = rng.random()
    if roll < 0.55:
        return f"{first} {surname}"
    if roll < 0.80:
        first = rng.choice(SPELLING_VARIANTS.get(first, (first,)))
        surname = rng.choice(SPELLING_VARIANTS.get(surname, (surname,)))
        return f"{first} {surname}"
    if roll < 0.90:
        return f"{surname} {first}"  # surname first, as some forms record it
    if roll < 0.96:
        return first  # surname left out
    return f"Km. {first} {surname}" if rng.random() < 0.5 else f"Shri {first} {surname}"


def _institutions(rng: random.Random) -> dict[str, Institution]:
    """Schools and colleges in every district, plus a few Top Class institutes."""
    institutions: dict[str, Institution] = {}
    for state in STATES:
        for district in state.districts:
            for i in range(4):
                code = f"{rng.randint(10, 38)}{_code(rng, 9)}"
                management = ("government", "government", "aided", "private")[i]
                recognised = i < 3 or rng.random() < 0.6
                name = (
                    f"{('Government', 'Government', 'Ekalavya Model', 'Adarsh')[i]} "
                    f"{'Residential ' if i == 2 else ''}School, {district}"
                )
                institutions[code] = Institution(
                    code, name, "school", state.name, district, recognised, False, management
                )
            for i in range(2):
                code = f"C-{_code(rng, 5)}"
                government = i == 0
                name = f"{'Government' if government else 'St. Xavier'} College, {district}"
                institutions[code] = Institution(
                    code,
                    name,
                    "college",
                    state.name,
                    district,
                    True,
                    government,
                    "government" if government else "aided",
                )
        code = f"U-{_code(rng, 4)}"
        institutions[code] = Institution(
            code,
            f"{state.name} University",
            "university",
            state.name,
            state.districts[0],
            True,
            True,
            "government",
        )
    top_class = (
        (1, "Indian Institute of Technology Delhi", "Delhi"),
        (31, "National Institute of Technology Rourkela", "Odisha"),
        (27, "National Institute of Technology Jamshedpur", "Jharkhand"),
        (257, "All India Institute of Medical Sciences, Deoghar", "Jharkhand"),
    )
    for serial, name, state in top_class:
        code = f"U-{_code(rng, 4)}"
        institutions[code] = Institution(
            code, name, "university", state, "", True, True, "government", top_class_id=serial
        )
    return institutions


@cache
def population(size: int = POPULATION_SIZE, seed: int = SEED) -> Population:
    rng = random.Random(seed)
    institutions = _institutions(rng)
    by_kind: dict[tuple[str, str], list[Institution]] = {}
    for inst in institutions.values():
        by_kind.setdefault((inst.kind, inst.state), []).append(inst)
    top_class = [inst for inst in institutions.values() if inst.top_class_id]
    levels, weights = zip(*EDUCATION_WEIGHTS, strict=True)
    academic_year_start = date(2026, 7, 1)

    people = []
    for index in range(size):
        state = rng.choice(STATES)
        district = rng.choice(state.districts)
        tribe = rng.choice(state.tribes) if rng.random() < 0.94 else None
        gender = rng.choice("MF")
        first, first_hi = rng.choice(MALE_NAMES if gender == "M" else FEMALE_NAMES)
        if tribe:
            surname, surname_hi = rng.choice(tribe.surnames)
        else:
            surname, surname_hi = rng.choice(
                (("Sharma", "शर्मा"), ("Yadav", "यादव"), ("Das", "दास"))
            )
        level = rng.choices(levels, weights)[0]
        typical_age = {
            "class_9": 14,
            "class_10": 15,
            "class_11": 16,
            "class_12": 17,
            "diploma": 18,
            "undergraduate": 19,
            "postgraduate": 22,
            "phd": 26,
            "postdoc": 31,
        }[level]
        age = typical_age + rng.choice((0, 0, 0, 1, 1, 2, 3, 5))
        born = academic_year_start - timedelta(days=age * 365 + rng.randint(0, 364))

        abroad = level in ("postgraduate", "phd", "postdoc") and rng.random() < 0.06
        if level.startswith("class_"):
            institution = rng.choice(
                [i for i in by_kind[("school", state.name)] if i.district == district]
            )
        elif abroad:
            institution = None
        elif level == "undergraduate" and rng.random() < 0.05:
            institution = rng.choice(top_class)
        elif level in ("phd", "postdoc", "postgraduate"):
            institution = rng.choice(
                by_kind[("university", state.name)] + by_kind[("college", state.name)]
            )
        else:
            colleges = by_kind[("college", state.name)]
            institution = rng.choice([i for i in colleges if i.district == district] or colleges)

        income = int(rng.lognormvariate(12.1, 0.55)) // 1000 * 1000
        has_bachelors = level in ("postgraduate", "phd", "postdoc")
        has_masters = level in ("phd", "postdoc")
        net_roll = (
            f"NET{_code(rng, 9)}"
            if has_masters or (level == "postgraduate" and rng.random() < 0.3)
            else None
        )
        net_result = None
        if net_roll:
            net_result = rng.choices(("JRF", "NET", None), (0.25, 0.35, 0.40))[0]

        has_record = rng.random() < 0.55
        award = "none"
        if has_record and tribe:
            award = {
                "class_9": "pre_matric",
                "class_10": "pre_matric",
                "phd": "nfst",
            }.get(level, "post_matric" if not abroad else "nos")
            if institution and institution.top_class_id:
                award = "top_class"

        person_id = f"P{index + 1:05d}"
        digest = hashlib.sha256(f"{seed}:{person_id}".encode()).hexdigest()
        people.append(
            Person(
                id=person_id,
                digilocker_id=f"dl-{digest[:12]}",
                uid_token=f"uid-{digest[12:36]}",
                uid_last4=f"{int(digest[36:44], 16) % 10000:04d}",
                phone=f"90{index + 1:08d}",
                first_name=first,
                first_name_hi=first_hi,
                surname=surname,
                surname_hi=surname_hi,
                gender=gender,
                date_of_birth=born,
                state=state,
                district=district,
                tribe=tribe,
                family_income=income,
                orphan=rng.random() < 0.02,
                education_level=level,
                institution=institution,
                abroad=abroad,
                bachelors_percent=round(rng.uniform(45, 88), 1) if has_bachelors else None,
                masters_percent=round(rng.uniform(48, 85), 1) if has_masters else None,
                net_roll_number=net_roll,
                net_result=net_result,
                bank_seeded=rng.random() < 0.82,
                disability_percent=rng.choice((0,) * 30 + (40, 60)),
                apaar_id=_code(rng, 12),
                has_caste_certificate=tribe is not None and rng.random() < 0.93,
                has_income_certificate=rng.random() < 0.85,
                stale_income_certificate=rng.random() < 0.15,
                caste_certificate_spelling=spelling(rng, first, surname),
                enrolled_in_udise=level.startswith("class_") and rng.random() < 0.97,
                has_scholarship_record=has_record,
                mota_award=award,
            )
        )
    return Population(tuple(people), institutions)
