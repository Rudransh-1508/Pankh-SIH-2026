from pankh_simulators.population import population

TOKEN = {"X-Phone-Token": "development-phone-token"}


def caller(client, call_sid: str, number: str):
    async def press(digits: str | None = None) -> dict:
        response = await client.post(
            "/v1/phone/ivr",
            headers=TOKEN,
            json={"call_sid": call_sid, "caller": number, "digits": digits},
        )
        assert response.status_code == 200, response.text
        return response.json()

    return press


async def test_an_unregistered_number_hears_only_general_information(client):
    press = caller(client, "CA1", "09123456780")
    welcome = await press()
    assert welcome["language"] == "hi,en"
    assert "For English, press 2" in welcome["say"]
    menu = await press("2")
    assert menu["say"].startswith("This number is not registered with Pankh")
    general = await press("5")
    assert "Pre-Matric scholarship" in general["say"]
    assert general["say"].endswith("For the menu, press 0. Or hang up.")
    refused = await press("1")
    assert refused["say"].startswith("Sorry, that key is not in the menu.")


async def test_a_student_hears_their_payments_in_hindi_and_asks_for_a_callback(
    client, sign_in, link_digilocker, official, sms
):
    person = population().by_id("P00176")
    tokens = await sign_in(f"+91{person.phone}")
    await link_digilocker({"Authorization": f"Bearer {tokens['access_token']}"}, person)

    # Exotel sends numbers with a leading 0.
    press = caller(client, "CA2", f"0{person.phone}")
    await press()
    menu = await press("1")
    assert menu["language"] == "hi"
    assert menu["say"].startswith("अपने आवेदन के लिए 1 दबाएँ")
    payments = await press("2")
    assert "₹" not in payments["say"]
    assert payments["say"].endswith("मेन्यू के लिए 0 दबाएँ। या कॉल काट दें।")

    callback = await press("9")
    assert callback["say"].startswith("आपके ज़िला कार्यालय से इसी नंबर पर वापस कॉल")
    again = await press("9")
    assert again["say"].startswith("आप आज पहले ही कॉल-बैक माँग चुके हैं")

    district = await official("district", person.state.name, person.district)
    (reminder,) = [
        r
        for r in (await client.get("/v1/review/nudges", headers=district)).json()
        if r["kind"] == "callback_request"
    ]
    assert person.phone in reminder["message"]
    done = await client.post(
        f"/v1/review/nudges/{reminder['id']}/decision",
        headers=district,
        json={"decision": "approve"},
    )
    assert done.json()["status"] == "sent"
    assert sms.texts == []  # marking a callback done sends nothing


async def test_exotel_gather_speaks_the_same_menu(client):
    response = await client.get(
        "/v1/phone/exotel/development-phone-token/gather",
        params={"CallSid": "EX1", "From": "09123456780"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "For English, press 2" in body["gather_prompt"]["text"]
    assert body["max_input_digits"] == 1
    second = await client.get(
        "/v1/phone/exotel/development-phone-token/gather",
        params={"CallSid": "EX1", "From": "09123456780", "digits": '"2"'},
    )
    assert second.json()["gather_prompt"]["text"].startswith("This number is not registered")


async def test_webhooks_need_the_token(client):
    assert (
        await client.post("/v1/phone/ivr", json={"call_sid": "x", "caller": "1"})
    ).status_code == 401
    wrong = await client.get(
        "/v1/phone/exotel/wrong/gather", params={"CallSid": "x", "From": "09123456780"}
    )
    assert wrong.status_code == 401
