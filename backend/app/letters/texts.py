"""Request letters a Student can print, copy or read out at an office. Formal, short, and filled
from the Student's own records; blanks are left where Pankh does not know a detail.
Lines are left long: this is prose.
"""

BLANK = "________"

LETTERS = {
    "income_certificate": {
        "en": {
            "title": "Request for an income certificate",
            "to": "The Tehsildar,\nTehsil office, {district}, {state}",
            "subject": "Request for an income certificate for the financial year {financial_year}",
            "body": "I, {name}, resident of {district}, {state}, request an income certificate for the financial year {financial_year}. I need it for the {scheme} scholarship of the Ministry of Tribal Affairs, which requires a certificate for the financial year before the academic session. My family's annual income from all sources is Rs. {income}. I enclose my Aadhaar card, my caste certificate and proof of my family's income.",
        },
        "hi": {
            "title": "आय प्रमाण पत्र के लिए आवेदन",
            "to": "श्रीमान तहसीलदार महोदय,\nतहसील कार्यालय, {district}, {state}",
            "subject": "वित्तीय वर्ष {financial_year} का आय प्रमाण पत्र जारी करने हेतु आवेदन",
            "body": "मैं, {name}, निवासी {district}, {state}, वित्तीय वर्ष {financial_year} का आय प्रमाण पत्र जारी करने का अनुरोध करता/करती हूँ। यह मुझे जनजातीय कार्य मंत्रालय की {scheme} छात्रवृत्ति के लिए चाहिए, जिसमें सत्र से पहले के वित्तीय वर्ष का प्रमाण पत्र आवश्यक है। मेरे परिवार की सभी स्रोतों से वार्षिक आय {income} रुपये है। मैं अपना आधार कार्ड, जाति प्रमाण पत्र और परिवार की आय का प्रमाण संलग्न कर रहा/रही हूँ।",
        },
    },
    "certificate_correction": {
        "en": {
            "title": "Request to correct the name on a certificate",
            "to": "The issuing officer,\n{issuer}",
            "subject": "Correction of my name on my {document}",
            "body": 'I, {name}, resident of {district}, {state}, request that my name on my {document} be corrected. The certificate spells it as "{name_on_document}", while my Aadhaar card, which is my identity record, reads "{name}". I need the correct name for the Ministry of Tribal Affairs scholarship. I enclose copies of my Aadhaar card and of the certificate.',
        },
        "hi": {
            "title": "प्रमाण पत्र में नाम सुधार के लिए आवेदन",
            "to": "जारीकर्ता अधिकारी महोदय,\n{issuer}",
            "subject": "मेरे {document} में नाम सुधार हेतु आवेदन",
            "body": 'मैं, {name}, निवासी {district}, {state}, अनुरोध करता/करती हूँ कि मेरे {document} में मेरा नाम सुधारा जाए। प्रमाण पत्र में नाम "{name_on_document}" लिखा है, जबकि मेरे आधार कार्ड में, जो मेरी पहचान का रिकॉर्ड है, नाम "{name}" है। जनजातीय कार्य मंत्रालय की छात्रवृत्ति के लिए मुझे सही नाम चाहिए। आधार कार्ड और प्रमाण पत्र की प्रतियाँ संलग्न हैं।',
        },
    },
    "bank_seeding": {
        "en": {
            "title": "Request to link Aadhaar to my account for DBT",
            "to": "The Branch Manager,\n{bank}",
            "subject": "Seeding of Aadhaar with my savings account for Direct Benefit Transfer",
            "body": "I, {name}, hold savings account number {account} at your branch. My scholarship from the Ministry of Tribal Affairs could not be credited because the account is not linked (seeded) with my Aadhaar for Direct Benefit Transfer. I request you to seed my Aadhaar with this account and map it with NPCI for DBT. I enclose a copy of my Aadhaar card and give my consent for its use for this purpose. My mobile number is {phone}.",
        },
        "hi": {
            "title": "डीबीटी के लिए खाते से आधार जोड़ने का आवेदन",
            "to": "श्रीमान शाखा प्रबंधक महोदय,\n{bank}",
            "subject": "प्रत्यक्ष लाभ अंतरण (डीबीटी) हेतु बचत खाते में आधार सीडिंग",
            "body": "मैं, {name}, आपकी शाखा में बचत खाता संख्या {account} का धारक/धारिका हूँ। जनजातीय कार्य मंत्रालय से मेरी छात्रवृत्ति जमा नहीं हो पाई, क्योंकि मेरा खाता डीबीटी के लिए आधार से जुड़ा (सीडेड) नहीं है। कृपया मेरे आधार को इस खाते से जोड़ें और डीबीटी के लिए एनपीसीआई पर मैप करें। आधार कार्ड की प्रति संलग्न है और इस कार्य के लिए मेरी सहमति है। मेरा मोबाइल नंबर {phone} है।",
        },
    },
    "bank_account_update": {
        "en": {
            "title": "Request to update my bank account",
            "to": "The Branch Manager,\n{bank}",
            "subject": "Updating my savings account so that my scholarship can be credited",
            "body": 'I, {name}, hold savings account number {account} at your branch. My scholarship from the Ministry of Tribal Affairs could not be credited: {reason} I request you to update my KYC and account details, with my name as on my Aadhaar card ("{name}"), so that the payment can be sent again. I enclose copies of my Aadhaar card and passbook. My mobile number is {phone}.',
        },
        "hi": {
            "title": "बैंक खाता अद्यतन करने का आवेदन",
            "to": "श्रीमान शाखा प्रबंधक महोदय,\n{bank}",
            "subject": "छात्रवृत्ति जमा होने हेतु बचत खाते का अद्यतन",
            "body": 'मैं, {name}, आपकी शाखा में बचत खाता संख्या {account} का धारक/धारिका हूँ। जनजातीय कार्य मंत्रालय से मेरी छात्रवृत्ति जमा नहीं हो पाई: {reason} कृपया मेरा केवाईसी और खाते का विवरण, आधार कार्ड के अनुसार मेरे नाम ("{name}") के साथ, अद्यतन करें, ताकि भुगतान फिर से भेजा जा सके। आधार कार्ड और पासबुक की प्रतियाँ संलग्न हैं। मेरा मोबाइल नंबर {phone} है।',
        },
    },
    "institute_request": {
        "en": {
            "title": "Request to my institute's scholarship nodal officer",
            "to": "The Scholarship Nodal Officer,\n{institute}",
            "subject": "My {scheme} scholarship application {application}",
            "body": "I, {name}, a student of your institution, request your help with my {scheme} scholarship application {application}. {reason} I request that the necessary correction or upload be made, or that I be told what I must provide, before the last date. My mobile number is {phone}.",
        },
        "hi": {
            "title": "संस्थान के छात्रवृत्ति नोडल अधिकारी को आवेदन",
            "to": "छात्रवृत्ति नोडल अधिकारी महोदय,\n{institute}",
            "subject": "मेरा {scheme} छात्रवृत्ति आवेदन {application}",
            "body": "मैं, {name}, आपके संस्थान का/की विद्यार्थी, अपने {scheme} छात्रवृत्ति आवेदन {application} में आपकी सहायता का अनुरोध करता/करती हूँ। {reason} कृपया अंतिम तिथि से पहले आवश्यक सुधार या अपलोड करें, या मुझे बताएँ कि मुझे क्या देना है। मेरा मोबाइल नंबर {phone} है।",
        },
    },
}

CLOSING = {
    "en": "Yours faithfully,\n\n{name}\nMobile: {phone}\nDate: {date}",
    "hi": "भवदीय/भवदीया,\n\n{name}\nमोबाइल: {phone}\nदिनांक: {date}",
}
