# Pankh

Pankh is a single place for Scheduled Tribe (ST) students to discover, apply for, and track scholarships, with the five Ministry of Tribal Affairs (MoTA) schemes as its core. It also gives the ministry a verification layer and a view of students who are eligible but not yet reached.

## Language

### Schemes and rules

**Scheme**:
A named scholarship or fellowship programme with its own guidelines, such as Pre-Matric, Post-Matric, Top Class, NFST or NOS.
_Avoid_: Scholarship (when meaning the programme), programme, yojana

**MoTA Scheme**:
One of the five schemes run by the Ministry of Tribal Affairs: Pre-Matric, Post-Matric, Top Class, National Fellowship (NFST) and National Overseas Scholarship (NOS).
_Avoid_: Core scheme, central scheme

**Catalogue Scheme**:
A scheme outside the five MoTA Schemes, shown to students for discovery only.
_Avoid_: Other scheme, external scheme

**Guideline**:
An official document issued for a Scheme, including its amendments and circulars, from which Rules are derived.
_Avoid_: Policy, notification (unless it is one)

**Rule**:
A single machine-checkable condition of a Scheme, tied to the Guideline paragraph it comes from and the academic years it applies to.
_Avoid_: Criterion, condition, check

**Rule Version**:
The set of Rules for a Scheme that was in force during a given academic year.
_Avoid_: Ruleset, policy version

**Eligibility Result**:
The outcome of judging one Student against one Scheme's Rule Version, listing which Rules passed, failed, or lacked facts.
_Avoid_: Match score, match percentage

**Exclusivity Rule**:
The ministry condition that a Student may hold only one MoTA Scheme award at a time.
_Avoid_: One-scheme rule, double-dipping check

**Scheme Path**:
A recommended sequence of Schemes across a Student's years of education that respects the Exclusivity Rule.
_Avoid_: Roadmap, plan, journey

### People

**Student**:
A person who applies for or may be eligible for a Scheme.
_Avoid_: User, applicant, beneficiary (except in ministry reporting)

**Guardian**:
A parent or carer who can see and act for one or more linked Students.
_Avoid_: Parent account, family account

**Facilitator**:
A teacher or field worker who registers or helps a Student with that Student's recorded Consent.
_Avoid_: Agent (reserved for software agents), volunteer, operator

**Reviewer**:
An official who resolves Exceptions at one Verification Level.
_Avoid_: Verifier, approver, admin

**Verification Level**:
One step in the official review chain: institute nodal officer, district, state, or ministry.
_Avoid_: Tier, stage

### Applications and money

**Source System**:
An existing system that holds the official record of an Application or its payments: NSP, SFMP (Canara Bank) or the NOS Portal.
_Avoid_: Portal (when meaning the system of record), backend

**Application**:
A Student's request for one Scheme in one academic year, whose official record lives in a Source System.
_Avoid_: Form, submission

**Application Stage**:
Where an Application currently sits: draft, submitted, under verification, sanctioned, disbursing, closed, or rejected.
_Avoid_: Status (too vague), step

**Renewal**:
A follow-on Application for the next academic year of a Scheme the Student already holds.
_Avoid_: Reapplication

**Sanction**:
The official approval of an Application for a stated amount.
_Avoid_: Approval, award letter

**Instalment**:
One payment tranche of a Sanction.
_Avoid_: Payment, transfer

**Disbursement Trace**:
The observed journey of one Instalment from Sanction to credit or failure, with a reason for any failure.
_Avoid_: Payment status, DBT status

### Documents and verification

**Document**:
A certificate or record a Student provides or that is pulled for them, such as an ST certificate, income certificate or marksheet.
_Avoid_: File, upload, attachment

**Referenced Document**:
A Document held by DigiLocker that Pankh stores only as a pointer, never as a copy.
_Avoid_: DigiLocker file, linked doc

**Uploaded Document**:
A Document the Student photographed or uploaded because no issuer holds it digitally.
_Avoid_: Manual document, scan

**Fact**:
A single piece of information about a Student, such as date of birth, family income or institution, along with where it came from.
_Avoid_: Field, attribute, profile data

**Data Source**:
A government or institutional register that can confirm Facts, such as DigiLocker, UIDAI, AISHE, UDISE+, APAAR, e-District or UGC-NTA.
_Avoid_: API, integration, provider

**Source Adapter**:
The single connection between Pankh and one Source System or Data Source, whether it points at the real service or a Simulator.
_Avoid_: Connector, integration, client

**Simulator**:
A stand-in for a Source System or Data Source that follows its published interface, used where real access is not available.
_Avoid_: Mock, fake, stub

**Proof**:
A signed record that a Fact was confirmed by a named Data Source at a stated time, with how well the values matched.
_Avoid_: Verification badge, verified flag

**Exception**:
A Fact that could not be confirmed or that conflicts between sources, sent to a Reviewer instead of blocking the Application.
_Avoid_: Error, failure, flag

**Deficiency**:
Something a Student must fix before an Application can move forward, raised by a Reviewer or a Source System.
_Avoid_: Issue, objection, query

**Consent**:
A Student's recorded permission for a specific pull of Facts or a specific action taken on their behalf.
_Avoid_: Agreement, permission (alone)

### Assistance

**JAGO**:
The single conversational front door, by text or voice, through which Students reach every Agent.
_Avoid_: Chatbot, bot, assistant

**Agent**:
A software worker with one job (intake, documents, deficiencies, chasing, and so on) that collects, explains, or follows up, but never decides eligibility or verification.
_Avoid_: Bot, AI (as a noun)

**Nudge**:
An outbound reminder an Agent sends to a Student, Guardian or official by app, SMS or phone.
_Avoid_: Notification (for the outbound act), alert, ping

### Coverage

**Record Link**:
A judged match between two records of the same person across different registers, with the evidence for the match.
_Avoid_: Join, dedupe, match (alone)

**Unreached Student**:
An ST student found in an education register (UDISE+, APAAR or OTR) who has no Application for any Scheme they appear eligible for.
_Avoid_: Missing beneficiary, gap student
