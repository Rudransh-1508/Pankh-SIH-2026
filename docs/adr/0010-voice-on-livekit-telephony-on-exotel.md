# Voice runs on LiveKit Agents; SMS and calls go through Exotel

One agent core must serve in-app voice, incoming calls and outbound calls. LiveKit Agents handles all three, including phone lines through SIP, so we do not build three voice pipelines. Speech recognition and output come from Bhashini, AI4Bharat or Sarvam, chosen per language by testing. Exotel is chosen over Twilio because Indian SMS and calls require DLT registration, which Exotel handles locally.
