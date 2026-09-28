"""What JAGO says, in every supported language. Kept apart from logic so it can be reviewed
by language editors. Lines are left long: this is prose.
"""

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi"}

TEXT = {
    "en": {
        "hello": "Namaste! I'm JAGO. I can tell you which scholarships you qualify for, where your "
        "applications are, why a payment has not reached you, and what to do about any problem.",
        "suggest": [
            "Which scholarships can I get?",
            "Where is my application?",
            "Has my money come?",
            "Any problem with my documents?",
        ],
        "saved": "Got it.",
        "not_understood": "I did not catch that. Please answer: {question}",
        "all_answered": "Thank you, that is everything I need.",
        "eligible": "You qualify for: {schemes}.",
        "none_eligible": "From your answers, none of the five scholarships fits this year.",
        "needs": "To know about {count} more {plural}, I have a few questions. {question}",
        "scheme_word": ("scheme", "schemes"),
        "not_linked": "Link DigiLocker in the Documents tab first, so I can find your applications.",
        "no_applications": "I could not find any scholarship application for you this year.",
        "unavailable": "The scholarship portals are not answering right now. Please try again later.",
        "waiting": "{scheme} ({system}): waiting at your {who} for {days} days.",
        "stalled": " That is longer than the official timeline.",
        "status": "{scheme} ({system}): {status}.",
        "fix": "To fix it: {fix}",
        "received": "{scheme}: ₹{amount} has reached your account.",
        "payment_problem": "{scheme}: instalment {number} did not reach you. {reason} {fix}",
        "no_payment_problem": "No payment problems. ",
        "no_money_yet": "No money has been paid yet for {scheme}.",
        "documents_ok": "Your documents have no problems.",
        "documents_not_linked": "You have not linked DigiLocker yet. Link it in the Documents tab and "
        "your certificates are checked automatically.",
        "reviewer_note": "The reviewer says: {note}",
        "scheme": "{name}: {summary} You get: {benefits}. Apply on {apply_on}.",
        "when": " When: {when}",
        "unknown": "I can help with scholarships, applications, payments and documents. Try one of these.",
    },
    "hi": {
        "hello": "नमस्ते! मैं JAGO हूँ। मैं बता सकता हूँ कि आपको कौन-सी छात्रवृत्ति मिल सकती है, "
        "आपका आवेदन कहाँ है, पैसा क्यों नहीं आया, और किसी दिक्कत में क्या करना है।",
        "suggest": [
            "मुझे कौन-सी छात्रवृत्ति मिल सकती है?",
            "मेरा आवेदन कहाँ है?",
            "क्या मेरा पैसा आया?",
            "मेरे दस्तावेज़ों में कोई दिक्कत?",
        ],
        "saved": "ठीक है।",
        "not_understood": "मैं समझ नहीं पाया। कृपया जवाब दें: {question}",
        "all_answered": "धन्यवाद, मुझे जो चाहिए था वह सब मिल गया।",
        "eligible": "आप इनके पात्र हैं: {schemes}।",
        "none_eligible": "आपके जवाबों के हिसाब से इस साल पाँचों में से कोई छात्रवृत्ति नहीं बनती।",
        "needs": "{count} और {plural} के बारे में जानने के लिए कुछ सवाल हैं। {question}",
        "scheme_word": ("योजना", "योजनाओं"),
        "not_linked": "पहले दस्तावेज़ टैब में डिजिलॉकर जोड़ें, ताकि मैं आपके आवेदन ढूँढ सकूँ।",
        "no_applications": "इस साल आपका कोई छात्रवृत्ति आवेदन नहीं मिला।",
        "unavailable": "छात्रवृत्ति पोर्टल अभी जवाब नहीं दे रहे। थोड़ी देर बाद फिर कोशिश करें।",
        "waiting": "{scheme} ({system}): {days} दिन से आपके {who} पर रुका है।",
        "stalled": " यह तय समय से ज़्यादा है।",
        "status": "{scheme} ({system}): {status}।",
        "fix": "ठीक करने के लिए: {fix}",
        "received": "{scheme}: ₹{amount} आपके खाते में आ चुके हैं।",
        "payment_problem": "{scheme}: किस्त {number} आप तक नहीं पहुँची। {reason} {fix}",
        "no_payment_problem": "भुगतान में कोई दिक्कत नहीं। ",
        "no_money_yet": "{scheme} के लिए अभी कोई पैसा नहीं आया है।",
        "documents_ok": "आपके दस्तावेज़ों में कोई दिक्कत नहीं है।",
        "documents_not_linked": "आपने अभी डिजिलॉकर नहीं जोड़ा है। दस्तावेज़ टैब में जोड़ें, आपके "
        "प्रमाणपत्र अपने आप जाँचे जाएँगे।",
        "reviewer_note": "जाँच अधिकारी का कहना है: {note}",
        "scheme": "{name}: {summary} आपको मिलेगा: {benefits}। आवेदन: {apply_on}।",
        "when": " कब: {when}",
        "unknown": "मैं छात्रवृत्ति, आवेदन, भुगतान और दस्तावेज़ों में मदद कर सकता हूँ। इनमें से कुछ पूछें।",
    },
}

WHO = {
    "en": {
        "institute": "institute",
        "district": "district office",
        "state": "state office",
        "sanctioning authority": "sanctioning office",
        "university": "university",
        "ministry": "Ministry",
    },
    "hi": {
        "institute": "संस्थान",
        "district": "ज़िला कार्यालय",
        "state": "राज्य कार्यालय",
        "sanctioning authority": "मंज़ूरी कार्यालय",
        "university": "विश्वविद्यालय",
        "ministry": "मंत्रालय",
    },
}

SYSTEM_PROMPT = """You are JAGO, the scholarship helper in the Pankh app for Scheduled Tribe students in India.
Reply in {language}, in short sentences and simple words, as if speaking to a student who may be
reading in a second language.

Rules you must follow:
- Use a tool for anything about the student, their applications, payments, documents or a scheme.
  Never guess. If a tool gives no answer, say you do not know.
- You never decide eligibility or verification yourself; repeat what the tools say.
- When a tool gives "what_to_do" or "fix", tell the student plainly.
- To learn more about the student, ask the question from next_question, one at a time. Save an
  answer with record_answer only when the student has clearly answered it.
- Do not ask for or repeat Aadhaar numbers, bank account numbers or passwords."""
