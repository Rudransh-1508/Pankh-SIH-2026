"""The words of outreach messages, in each language. Fixed templates, never generated.

Every message names the ministry, says applying is free, and (to families) warns that nobody
will ask for money or a code, because scholarship fraud targets exactly these families.
"""

from app.languages import Language

_SCHOOL = {
    "en": (
        "Pankh, Ministry of Tribal Affairs: {count} ST students at {school} may qualify for "
        "{schemes} but have not applied. The list, with what each can apply for: {link} "
        "(valid for 30 days)."
    ),
    "hi": (
        "पंख, जनजातीय कार्य मंत्रालय: {school} के {count} अनुसूचित जनजाति विद्यार्थी {schemes} "
        "के पात्र हो सकते हैं, पर उन्होंने आवेदन नहीं किया है। सूची और हर विद्यार्थी की योजना: "
        "{link} (30 दिन मान्य)।"
    ),
    "bn": (
        "পঙ্খ, জনজাতি বিষয়ক মন্ত্রক: {school}-এর {count} জন তফসিলি উপজাতি ছাত্রছাত্রী {schemes}-এর "
        "যোগ্য হতে পারে, কিন্তু আবেদন করেনি। তালিকা, কে কীসের জন্য আবেদন করতে পারে সহ: {link} "
        "(30 দিন বৈধ)।"
    ),
    "gu": (
        "પંખ, આદિજાતિ બાબતોનું મંત્રાલય: {school}ના {count} અનુસૂચિત જનજાતિ વિદ્યાર્થીઓ {schemes} "
        "માટે પાત્ર હોઈ શકે છે, પણ તેમણે અરજી કરી નથી. યાદી અને દરેક શેના માટે અરજી કરી શકે: "
        "{link} (30 દિવસ માન્ય)."
    ),
    "mr": (
        "पंख, आदिवासी कार्य मंत्रालय: {school} मधील {count} अनुसूचित जमातीचे विद्यार्थी {schemes} "
        "साठी पात्र असू शकतात, पण त्यांनी अर्ज केलेला नाही. यादी आणि प्रत्येकजण कशासाठी अर्ज "
        "करू शकतो: {link} (30 दिवस वैध)."
    ),
    "or": (
        "ପଙ୍ଖ, ଜନଜାତି ବ୍ୟାପାର ମନ୍ତ୍ରଣାଳୟ: {school}ର {count} ଜଣ ଅନୁସୂଚିତ ଜନଜାତି ଛାତ୍ରଛାତ୍ରୀ "
        "{schemes} ପାଇଁ ଯୋଗ୍ୟ ହୋଇପାରନ୍ତି, କିନ୍ତୁ ଆବେଦନ କରିନାହାନ୍ତି। ତାଲିକା ଓ ପ୍ରତ୍ୟେକେ କେଉଁଥିପାଇଁ "
        "ଆବେଦନ କରିପାରିବେ: {link} (30 ଦିନ ବୈଧ)।"
    ),
}

_FAMILY = {
    "en": (
        "Pankh, Ministry of Tribal Affairs: {name} may qualify for the {schemes} scholarship. "
        "Applying is free: ask at your school or use the Pankh app. Nobody will ask you for "
        "money or an OTP."
    ),
    "hi": (
        "पंख, जनजातीय कार्य मंत्रालय: {name} को {schemes} छात्रवृत्ति मिल सकती है। आवेदन "
        "निःशुल्क है: अपने स्कूल में पूछें या पंख ऐप का उपयोग करें। कोई भी आपसे पैसे या OTP "
        "नहीं माँगेगा।"
    ),
    "bn": (
        "পঙ্খ, জনজাতি বিষয়ক মন্ত্রক: {name} {schemes} বৃত্তি পেতে পারে। আবেদন বিনামূল্যে: আপনার "
        "স্কুলে জিজ্ঞেস করুন বা পঙ্খ অ্যাপ ব্যবহার করুন। কেউ আপনার কাছে টাকা বা OTP চাইবে না।"
    ),
    "gu": (
        "પંખ, આદિજાતિ બાબતોનું મંત્રાલય: {name}ને {schemes} શિષ્યવૃત્તિ મળી શકે છે. અરજી મફત છે: "
        "તમારી શાળામાં પૂછો અથવા પંખ ઍપ વાપરો. કોઈ તમારી પાસે પૈસા કે OTP માંગશે નહીં."
    ),
    "mr": (
        "पंख, आदिवासी कार्य मंत्रालय: {name} ला {schemes} शिष्यवृत्ती मिळू शकते. अर्ज विनामूल्य "
        "आहे: तुमच्या शाळेत विचारा किंवा पंख ॲप वापरा. कोणीही तुमच्याकडे पैसे किंवा OTP मागणार नाही."
    ),
    "or": (
        "ପଙ୍ଖ, ଜନଜାତି ବ୍ୟାପାର ମନ୍ତ୍ରଣାଳୟ: {name} {schemes} ଛାତ୍ରବୃତ୍ତି ପାଇପାରନ୍ତି। ଆବେଦନ ମାଗଣା: "
        "ଆପଣଙ୍କ ସ୍କୁଲରେ ପଚାରନ୍ତୁ ବା ପଙ୍ଖ ଆପ୍ ବ୍ୟବହାର କରନ୍ତୁ। କେହି ଆପଣଙ୍କୁ ଟଙ୍କା ବା OTP ମାଗିବେ ନାହିଁ।"
    ),
}

_OR = {"en": " or ", "hi": " या ", "bn": " বা ", "gu": " અથવા ", "mr": " किंवा ", "or": " ବା "}


def _schemes(names: list[str], language: Language) -> str:
    unique = list(dict.fromkeys(names))
    if len(unique) <= 1:
        return "".join(unique)
    return ", ".join(unique[:-1]) + _OR[language] + unique[-1]


def school_message(
    language: Language, school: str, count: int, schemes: list[str], link: str
) -> str:
    return _SCHOOL[language].format(
        school=school, count=count, schemes=_schemes(schemes, language), link=link
    )


def family_message(language: Language, name: str, schemes: list[str]) -> str:
    first_name = name.split()[0] if name.split() else name
    return _FAMILY[language].format(name=first_name, schemes=_schemes(schemes, language))
