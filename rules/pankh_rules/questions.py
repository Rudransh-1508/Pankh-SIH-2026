"""How each Fact is asked of a Student, in every supported language.

Questions are written in the second person, in plain words, for one question per screen.
"""

LANGUAGES = ("en", "hi")

# Facts that can rule out whole Schemes on their own are asked before anything else.
GATING_FACTS = ("is_scheduled_tribe", "education_level", "studies_abroad")

QUESTIONS: dict[str, dict[str, str]] = {
    "gender": {
        "en": "What is your gender?",
        "hi": "आपका लिंग क्या है?",
    },
    "studies_by_distance": {
        "en": "Are you studying by correspondence or distance learning?",
        "hi": "क्या आप पत्राचार या दूरस्थ शिक्षा से पढ़ रहे हैं?",
    },
    "class_12_top_20_percent": {
        "en": "In Class XII, were you in the top 20% of students who passed in your stream on your "
        "board?",
        "hi": "क्या कक्षा 12 में आप अपने बोर्ड और स्ट्रीम के पास हुए छात्रों में शीर्ष 20% में थे?",
    },
    "aicte_technical_first_year": {
        "en": "Are you in the first year of a technical degree (such as B.Tech) at an AICTE-approved "
        "college, or the second year by lateral entry?",
        "hi": "क्या आप AICTE से मान्यता प्राप्त कॉलेज में तकनीकी डिग्री (जैसे B.Tech) के पहले साल में हैं, "
        "या लेटरल एंट्री से दूसरे साल में?",
    },
    "joined_within_two_years_of_class_12": {
        "en": "Did you join your degree within two years of passing Class XII?",
        "hi": "क्या आपने कक्षा 12 पास करने के दो साल के भीतर डिग्री में दाखिला लिया?",
    },
    "selected_in_nmms_exam": {
        "en": "Were you selected in the NMMS scholarship exam in Class VIII?",
        "hi": "क्या कक्षा 8 में NMMS छात्रवृत्ति परीक्षा में आपका चयन हुआ था?",
    },
    "school_government_aided_or_local_body": {
        "en": "Is your school a government, government-aided or local body school? (Not a Kendriya "
        "Vidyalaya, Navodaya, residential or private school.)",
        "hi": "क्या आपका स्कूल सरकारी, सरकारी सहायता प्राप्त या स्थानीय निकाय का है? (केंद्रीय "
        "विद्यालय, नवोदय, आवासीय या निजी स्कूल नहीं।)",
    },
    "is_scheduled_tribe": {
        "en": "Do you belong to a Scheduled Tribe (ST) of your state?",
        "hi": "क्या आप अपने राज्य की अनुसूचित जनजाति (ST) से हैं?",
    },
    "education_level": {
        "en": "What are you studying this year, or applying to study?",
        "hi": "इस साल आप क्या पढ़ रहे हैं, या किस पढ़ाई के लिए आवेदन कर रहे हैं?",
    },
    "studies_abroad": {
        "en": "Is your course outside India?",
        "hi": "क्या आपका कोर्स भारत के बाहर है?",
    },
    "institution_recognised": {
        "en": "Is your school or college run or recognised by the government?",
        "hi": "क्या आपका स्कूल या कॉलेज सरकारी है या सरकार से मान्यता प्राप्त है?",
    },
    "institution_eligible_for_fellowship": {
        "en": "Is your university UGC-recognised (2(f) or 12(B)), government-funded, or an "
        "Institute of National Importance?",
        "hi": "क्या आपका विश्वविद्यालय UGC से मान्यता प्राप्त (2(f) या 12(B)), सरकारी अनुदान "
        "प्राप्त, या राष्ट्रीय महत्व का संस्थान है?",
    },
    "admitted_to_top_class_institute": {
        "en": "Have you got admission to an institute on the Top Class list?",
        "hi": "क्या आपको टॉप क्लास सूची के किसी संस्थान में दाखिला मिला है?",
    },
    "admitted_via_management_quota": {
        "en": "Was your admission through a management quota?",
        "hi": "क्या आपका दाखिला मैनेजमेंट कोटे से हुआ है?",
    },
    "family_income": {
        "en": "What is your family's total income in a year?",
        "hi": "आपके परिवार की सालाना कुल आय कितनी है?",
    },
    "is_orphan_supported_by_guardian": {
        "en": "Have you lost both parents, and does a guardian support you?",
        "hi": "क्या आपके माता-पिता दोनों नहीं हैं, और कोई अभिभावक आपकी देखभाल करते हैं?",
    },
    "date_of_birth": {
        "en": "What is your date of birth?",
        "hi": "आपकी जन्म तिथि क्या है?",
    },
    "repeating_stage_in_other_subject": {
        "en": "Are you studying again at a level you have already passed, in a different "
        "subject? For example, B.Com after B.A.",
        "hi": "क्या आप वही स्तर दोबारा किसी दूसरे विषय में पढ़ रहे हैं, जो आप पहले पास कर "
        "चुके हैं? जैसे B.A. के बाद B.Com.",
    },
    "bachelors_marks_percent": {
        "en": "What percentage did you get in your Bachelor's degree?",
        "hi": "स्नातक (बैचलर) डिग्री में आपके कितने प्रतिशत अंक आए?",
    },
    "masters_marks_percent": {
        "en": "What percentage did you get in your Master's degree?",
        "hi": "स्नातकोत्तर (मास्टर्स) डिग्री में आपके कितने प्रतिशत अंक आए?",
    },
    "net_jrf_qualified": {
        "en": "Have you qualified UGC NET or Joint CSIR-UGC NET?",
        "hi": "क्या आपने UGC NET या संयुक्त CSIR-UGC NET पास किया है?",
    },
    "has_overseas_admission_offer": {
        "en": "Do you have an offer of admission from a university abroad?",
        "hi": "क्या आपके पास विदेश के किसी विश्वविद्यालय से दाखिले का प्रस्ताव है?",
    },
    "overseas_admission_in_qs_top_1000": {
        "en": "Is that university in the top 1,000 of the QS World University Rankings?",
        "hi": "क्या वह विश्वविद्यालय QS वर्ल्ड यूनिवर्सिटी रैंकिंग के शीर्ष 1,000 में है?",
    },
    "sibling_received_nos": {
        "en": "Has your brother or sister already received the National Overseas Scholarship?",
        "hi": "क्या आपके भाई या बहन को पहले से राष्ट्रीय प्रवासी छात्रवृत्ति मिल चुकी है?",
    },
    "previously_received_nos": {
        "en": "Have you received the National Overseas Scholarship before?",
        "hi": "क्या आपको पहले कभी राष्ट्रीय प्रवासी छात्रवृत्ति मिली है?",
    },
    "current_mota_award": {
        "en": "Do you already get a scholarship from the Ministry of Tribal Affairs?",
        "hi": "क्या आपको पहले से जनजातीय कार्य मंत्रालय की कोई छात्रवृत्ति मिल रही है?",
    },
    "holds_other_scholarship": {
        "en": "Do you get any other scholarship, fellowship or stipend right now?",
        "hi": "क्या अभी आपको कोई और छात्रवृत्ति, फेलोशिप या स्टाइपेंड मिल रहा है?",
    },
    "has_aadhaar_seeded_bank_account": {
        "en": "Do you have a bank account linked to your Aadhaar and mobile number?",
        "hi": "क्या आपका बैंक खाता आपके आधार और मोबाइल नंबर से जुड़ा है?",
    },
}

HELP: dict[str, dict[str, str]] = {
    "family_income": {
        "en": "Add up your parents' income from all sources. If you are married, add your "
        "spouse's income. Don't count brothers, sisters or other relatives.",
        "hi": "माता-पिता की सभी स्रोतों से आय जोड़ें। अगर आप विवाहित हैं, तो जीवनसाथी की आय "
        "भी जोड़ें। भाई-बहन या अन्य रिश्तेदारों की आय न जोड़ें।",
    },
    "institution_recognised": {
        "en": "Your school or college can tell you. Recognised schools have a U-DISE code; "
        "colleges have an AISHE code.",
        "hi": "आपका स्कूल या कॉलेज यह बता सकता है। मान्यता प्राप्त स्कूलों का U-DISE कोड होता "
        "है; कॉलेजों का AISHE कोड होता है।",
    },
}

CHOICE_LABELS: dict[str, dict[str, dict[str, str]]] = {
    "gender": {
        "female": {"en": "Female", "hi": "महिला"},
        "male": {"en": "Male", "hi": "पुरुष"},
        "other": {"en": "Other", "hi": "अन्य"},
    },
    "education_level": {
        "class_9": {"en": "Class IX", "hi": "कक्षा 9"},
        "class_10": {"en": "Class X", "hi": "कक्षा 10"},
        "class_11": {"en": "Class XI", "hi": "कक्षा 11"},
        "class_12": {"en": "Class XII", "hi": "कक्षा 12"},
        "diploma": {"en": "Diploma or ITI", "hi": "डिप्लोमा या ITI"},
        "undergraduate": {"en": "Bachelor's degree", "hi": "स्नातक (बैचलर) डिग्री"},
        "postgraduate": {"en": "Master's degree", "hi": "स्नातकोत्तर (मास्टर्स) डिग्री"},
        "mphil": {"en": "M.Phil", "hi": "एम.फिल"},
        "phd": {"en": "Ph.D", "hi": "पीएच.डी"},
        "postdoc": {"en": "Post-doctoral research", "hi": "पोस्ट-डॉक्टरल शोध"},
    },
    "current_mota_award": {
        "none": {"en": "No", "hi": "नहीं"},
        "pre_matric": {"en": "Yes, Pre-Matric", "hi": "हाँ, प्री-मैट्रिक"},
        "post_matric": {"en": "Yes, Post-Matric", "hi": "हाँ, पोस्ट-मैट्रिक"},
        "top_class": {"en": "Yes, Top Class", "hi": "हाँ, टॉप क्लास"},
        "nfst": {"en": "Yes, National Fellowship (NFST)", "hi": "हाँ, राष्ट्रीय फेलोशिप (NFST)"},
        "nos": {
            "en": "Yes, National Overseas Scholarship (NOS)",
            "hi": "हाँ, राष्ट्रीय प्रवासी छात्रवृत्ति (NOS)",
        },
    },
}
