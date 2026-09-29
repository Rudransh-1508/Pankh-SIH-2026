import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pankh/app.dart';
import 'package:pankh/data/voice_line.dart';

import 'support.dart';

class FakeVoiceCall implements VoiceCall {
  final lineController = StreamController<VoiceLine>.broadcast();
  final speakingController = StreamController<bool>.broadcast();
  String? joined;
  bool muted = false;
  bool hungUp = false;

  @override
  Stream<VoiceLine> get lines => lineController.stream;

  @override
  Stream<bool> get jagoSpeaking => speakingController.stream;

  @override
  Future<void> connect(String url, String token) async => joined = '$url $token';

  @override
  Future<void> setMuted(bool value) async => muted = value;

  @override
  Future<void> hangUp() async => hungUp = true;
}

void main() {
  testWidgets('a spoken conversation is written out, and ends when the Student hangs up', (
    tester,
  ) async {
    final call = FakeVoiceCall();
    final (app, _, _) = await buildApp(
      facts: {'is_scheduled_tribe': true},
      phone: '+919876543210',
      voiceCall: call,
    );
    await tester.pumpWidget(app);
    await tester.pumpAndSettle();
    final container = ProviderScope.containerOf(tester.element(find.byType(MaterialApp)));
    unawaited(container.read(routerProvider).push('/voice'));
    await tester.pumpAndSettle();

    expect(call.joined, 'wss://pankh-test.livekit.cloud room-token');
    expect(find.text('Listening. Speak now.'), findsOneWidget);
    call.lineController.add(
      const VoiceLine(fromStudent: true, text: 'Which scholarships can I get?'),
    );
    call.speakingController.add(true);
    call.lineController.add(
      const VoiceLine(fromStudent: false, text: 'You qualify for Pre-Matric.'),
    );
    await tester.pumpAndSettle();
    expect(find.text('JAGO is speaking'), findsOneWidget);
    expect(find.text('Which scholarships can I get?'), findsOneWidget);
    expect(find.text('You qualify for Pre-Matric.'), findsOneWidget);

    await tester.tap(find.text('Mute'));
    await tester.pumpAndSettle();
    expect(call.muted, isTrue);
    await tester.tap(find.text('End'));
    await tester.pumpAndSettle();
    expect(call.hungUp, isTrue);
  });
}
