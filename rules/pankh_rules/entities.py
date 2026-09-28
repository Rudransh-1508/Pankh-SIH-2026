from openfisca_core.entities import build_entity

Student = build_entity(
    key="student",
    plural="students",
    label="Student",
    doc="A person who applies for, or may be eligible for, a Scheme.",
    is_person=True,
)

entities = [Student]
