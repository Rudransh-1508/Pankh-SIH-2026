import 'dart:io';

import 'package:path_provider/path_provider.dart';

import 'api.dart';
import 'document_capture.dart';
import 'local_store.dart';
import 'models.dart';

/// Photos taken without a connection wait here, in the app's private storage, and upload the
/// next time the Documents tab loads with a connection.
class UploadQueue {
  UploadQueue(this._store, this._api, {Future<Directory> Function()? directory})
    : _directory = directory ?? getApplicationSupportDirectory;

  final LocalStore _store;
  final PankhApi _api;
  final Future<Directory> Function() _directory;

  List<Json> get pending => _store.pendingUploads;

  /// Keep a copy of the photo, since the camera's file may be cleaned up by the system.
  Future<void> add(String kind, CapturedDocument captured) async {
    final folder = Directory('${(await _directory()).path}/pending_uploads');
    await folder.create(recursive: true);
    final copy = await File(
      captured.path,
    ).copy('${folder.path}/${DateTime.now().microsecondsSinceEpoch}_$kind.jpg');
    await _store.setPendingUploads([
      ...pending,
      {
        'kind': kind,
        'path': copy.path,
        'content_type': captured.contentType,
        'text': captured.text,
      },
    ]);
  }

  /// Upload what is waiting. Stops at the first sign the phone is still offline.
  Future<List<UploadOutcome>> flush() async {
    final outcomes = <UploadOutcome>[];
    final remaining = [...pending];
    while (remaining.isNotEmpty) {
      final upload = remaining.first;
      final file = File(upload['path'] as String);
      if (!file.existsSync()) {
        remaining.removeAt(0);
        continue;
      }
      try {
        outcomes.add(
          UploadOutcome.fromJson(
            await _api.uploadDocument(
              kind: upload['kind'] as String,
              path: file.path,
              contentType: upload['content_type'] as String,
              text: upload['text'] as String,
            ),
          ),
        );
      } on ApiException catch (error) {
        if (error.isOffline) break;
        // Refused for good (too large, say): the Student sees why when they try again.
      }
      remaining.removeAt(0);
      await file.delete().catchError((_) => file);
    }
    await _store.setPendingUploads(remaining);
    return outcomes;
  }
}
