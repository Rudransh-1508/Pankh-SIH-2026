import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';

/// A photo of a Document, with the text read from it on the phone.
class CapturedDocument {
  const CapturedDocument({required this.path, required this.contentType, required this.text});

  final String path;
  final String contentType;
  final String text;
}

/// Takes a photo of a Document and reads its text on the device, in Latin and Devanagari
/// scripts. Nothing leaves the phone until the Student uploads it.
class DocumentCapture {
  DocumentCapture({ImagePicker? picker}) : _picker = picker ?? ImagePicker();

  final ImagePicker _picker;

  /// Null when the Student cancels.
  Future<CapturedDocument?> capture({required bool fromCamera}) async {
    final photo = await _picker.pickImage(
      source: fromCamera ? ImageSource.camera : ImageSource.gallery,
      // Large enough to read small print, small enough to upload on a slow connection.
      maxWidth: 2400,
      maxHeight: 2400,
      imageQuality: 85,
      requestFullMetadata: false,
    );
    if (photo == null) return null;
    final input = InputImage.fromFilePath(photo.path);
    final texts = <String>[];
    for (final script in [TextRecognitionScript.latin, TextRecognitionScript.devanagiri]) {
      final recognizer = TextRecognizer(script: script);
      try {
        texts.add((await recognizer.processImage(input)).text);
      } finally {
        await recognizer.close();
      }
    }
    final lower = photo.path.toLowerCase();
    return CapturedDocument(
      path: photo.path,
      contentType: lower.endsWith('.png') ? 'image/png' : 'image/jpeg',
      text: texts.join('\n'),
    );
  }
}
