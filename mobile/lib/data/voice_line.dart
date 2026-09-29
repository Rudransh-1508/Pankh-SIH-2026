import 'dart:async';

import 'package:livekit_client/livekit_client.dart';

/// One line of a spoken conversation, as transcribed.
class VoiceLine {
  const VoiceLine({required this.fromStudent, required this.text});

  final bool fromStudent;
  final String text;
}

/// A live voice conversation with JAGO. Behind an interface so screens can be tested without
/// audio or a network.
abstract class VoiceCall {
  /// Lines as they are transcribed, and whether JAGO is speaking right now.
  Stream<VoiceLine> get lines;
  Stream<bool> get jagoSpeaking;

  Future<void> connect(String url, String token);
  Future<void> setMuted(bool muted);
  Future<void> hangUp();
}

/// A voice conversation over LiveKit: the phone's microphone goes to the JAGO agent, and its
/// voice and transcripts come back.
class LiveKitVoiceCall implements VoiceCall {
  final _room = Room(roomOptions: const RoomOptions(adaptiveStream: true, dynacast: true));
  final _lines = StreamController<VoiceLine>.broadcast();
  final _speaking = StreamController<bool>.broadcast();
  EventsListener<RoomEvent>? _events;

  @override
  Stream<VoiceLine> get lines => _lines.stream;

  @override
  Stream<bool> get jagoSpeaking => _speaking.stream;

  @override
  Future<void> connect(String url, String token) async {
    _room.registerTextStreamHandler('lk.transcription', (reader, identity) async {
      final text = (await reader.readAll()).trim();
      final isFinal = reader.info?.attributes['lk.transcription_final'] == 'true';
      if (text.isNotEmpty && isFinal) {
        _lines.add(VoiceLine(fromStudent: identity.startsWith('student-'), text: text));
      }
    });
    _events = _room.createListener()
      ..on<ActiveSpeakersChangedEvent>((event) {
        _speaking.add(event.speakers.any((p) => !p.identity.startsWith('student-')));
      });
    await _room.connect(url, token);
    await _room.localParticipant?.setMicrophoneEnabled(true);
  }

  @override
  Future<void> setMuted(bool muted) async => _room.localParticipant?.setMicrophoneEnabled(!muted);

  @override
  Future<void> hangUp() async {
    await _events?.dispose();
    await _room.disconnect();
    await _room.dispose();
    await _lines.close();
    await _speaking.close();
  }
}
