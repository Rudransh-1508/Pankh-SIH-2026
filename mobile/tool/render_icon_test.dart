// Renders the FeatherMark into the launcher icon images in assets/icon/.
// Run from mobile/: flutter test tool/render_icon_test.dart && dart run flutter_launcher_icons
import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pankh/theme.dart';
import 'package:pankh/widgets/feather_mark.dart';

const _size = 1024.0;

Future<void> _render(WidgetTester tester, String path, {required bool withBackground, required double featherScale}) async {
  final key = GlobalKey();
  await tester.pumpWidget(
    Directionality(
      textDirection: TextDirection.ltr,
      child: Center(
        child: RepaintBoundary(
          key: key,
          child: Container(
            width: _size,
            height: _size,
            color: withBackground ? PankhColors.paper : Colors.transparent,
            alignment: Alignment.center,
            child: FeatherMark(size: _size * featherScale),
          ),
        ),
      ),
    ),
  );
  await tester.runAsync(() async {
    final boundary = key.currentContext!.findRenderObject()! as RenderRepaintBoundary;
    final image = await boundary.toImage();
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    File(path).writeAsBytesSync(bytes!.buffer.asUint8List());
  });
}

void main() {
  testWidgets('render launcher icons', (tester) async {
    tester.view.physicalSize = const Size(_size, _size);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    // Full icon for iOS and legacy Android.
    await _render(tester, 'assets/icon/icon.png', withBackground: true, featherScale: 0.72);
    // Adaptive icon foreground: kept inside the central safe zone, which is about 61% wide.
    await _render(tester, 'assets/icon/foreground.png', withBackground: false, featherScale: 0.5);
  });
}
