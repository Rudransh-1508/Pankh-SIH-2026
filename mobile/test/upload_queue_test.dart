import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:pankh/data/api.dart';
import 'package:pankh/data/document_capture.dart';
import 'package:pankh/data/local_store.dart';
import 'package:pankh/data/models.dart';
import 'package:pankh/data/upload_queue.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'support.dart';

class _FlakyApi extends FakeApi {
  bool online = false;
  final uploaded = <String>[];

  @override
  Future<Json> uploadDocument({
    required String kind,
    required String path,
    required String contentType,
    required String text,
  }) async {
    if (!online) throw const ApiException('offline', isOffline: true);
    uploaded.add('$kind:$text');
    return {
      'readable': true,
      'message': 'Sent to an officer',
      'problems': <dynamic>[],
      'verified_facts': <dynamic>[],
      'document': null,
    };
  }
}

void main() {
  test('photos taken offline are kept and uploaded once back online', () async {
    SharedPreferences.setMockInitialValues({});
    final store = LocalStore(await SharedPreferences.getInstance());
    final folder = await Directory.systemTemp.createTemp('pankh_queue');
    final photo = File('${folder.path}/camera.jpg')..writeAsBytesSync([0xff, 0xd8, 0xff, 1]);
    final api = _FlakyApi();
    final queue = UploadQueue(store, api, directory: () async => folder);

    await queue.add(
      'income_certificate',
      CapturedDocument(path: photo.path, contentType: 'image/jpeg', text: 'Annual income'),
    );
    photo.deleteSync(); // the camera's own file may be cleaned up; the queue has its copy
    expect(queue.pending, hasLength(1));

    expect(await queue.flush(), isEmpty);
    expect(queue.pending, hasLength(1));

    api.online = true;
    final outcomes = await queue.flush();
    expect(outcomes.single.message, 'Sent to an officer');
    expect(api.uploaded, ['income_certificate:Annual income']);
    expect(queue.pending, isEmpty);
    expect(Directory('${folder.path}/pending_uploads').listSync(), isEmpty);
  });
}
