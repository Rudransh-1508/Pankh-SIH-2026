import 'dart:async';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import 'local_store.dart';
import 'models.dart';

/// A failure the Student can act on. [message] is ready to show.
class ApiException implements Exception {
  const ApiException(this.message, {this.isOffline = false, this.statusCode});

  final String message;
  final bool isOffline;
  final int? statusCode;

  @override
  String toString() => message;
}

class OtpRequested {
  const OtpRequested({
    required this.phone,
    required this.resendAfter,
    this.demoCode,
    this.bySms = false,
  });

  final String phone;
  final int resendAfter;

  /// Only on a demo deployment, for the synthetic demo numbers, which get no SMS.
  final String? demoCode;

  /// True when the code was sent by real SMS (Firebase), false when the API issued it.
  final bool bySms;
}

/// Talks to the Pankh API. Signed-in requests refresh the access token automatically.
class PankhApi {
  PankhApi({required String baseUrl, required TokenStore tokens, Dio? dio})
    : _tokens = tokens,
      _dio =
          dio ??
          Dio(
            BaseOptions(
              baseUrl: '$baseUrl/v1',
              connectTimeout: const Duration(seconds: 10),
              receiveTimeout: const Duration(seconds: 20),
              contentType: 'application/json',
            ),
          ) {
    _dio.interceptors.add(
      QueuedInterceptorsWrapper(onRequest: _attachToken, onError: _refreshOnUnauthorised),
    );
  }

  final Dio _dio;
  final TokenStore _tokens;

  /// Called when the session has ended and the Student must sign in again.
  void Function()? onSignedOut;

  Future<OtpRequested> requestOtp(String phone) async {
    final json = await _send(() => _dio.post('/auth/otp/request', data: {'phone': phone}));
    return OtpRequested(
      phone: json['phone'] as String,
      resendAfter: json['resend_after'] as int,
      demoCode: json['demo_code'] as String?,
    );
  }

  Future<void> verifyOtp(String phone, String code) async {
    final json = await _send(
      () => _dio.post('/auth/otp/verify', data: {'phone': phone, 'code': code}),
    );
    await _tokens.save(
      access: json['access_token'] as String,
      refresh: json['refresh_token'] as String,
    );
  }

  /// Sign in with the ID token Firebase gave after confirming the number by SMS.
  Future<void> signInWithSms(String idToken) async {
    final json = await _send(() => _dio.post('/auth/firebase', data: {'id_token': idToken}));
    await _tokens.save(
      access: json['access_token'] as String,
      refresh: json['refresh_token'] as String,
    );
  }

  Future<void> signOut() async {
    final refresh = await _tokens.refreshToken();
    await _tokens.clear();
    if (refresh != null) {
      try {
        await _dio.post('/auth/sign-out', data: {'refresh_token': refresh});
      } on DioException {
        // The session is already forgotten on this phone; the server copy expires on its own.
      }
    }
  }

  /// The Fact schema as returned by the API, so it can be cached as is.
  Future<List<dynamic>> factSchema() => _sendList(() => _dio.get('/facts/schema'));

  Future<Json> myFacts() async => (await _send(() => _dio.get('/me/facts')))['facts'] as Json;

  Future<void> saveFacts(Json facts) =>
      _send(() => _dio.patch('/me/facts', data: {'facts': facts}));

  /// Eligibility for the signed-in Student, from the Facts stored on the server.
  Future<Json> myEligibility() => _send(() => _dio.get('/me/eligibility'));

  /// Eligibility from Facts held on the phone, without signing in. Nothing is stored.
  Future<Json> eligibility(Json facts) =>
      _send(() => _dio.post('/eligibility', data: {'facts': facts}));

  /// Starts linking DigiLocker. Open the returned address; DigiLocker returns to the app.
  Future<String> startDigiLocker() async =>
      (await _send(() => _dio.post('/me/digilocker/start')))['authorization_url'] as String;

  Future<Json> completeDigiLocker(String code, String state) =>
      _send(() => _dio.post('/me/digilocker/complete', data: {'code': code, 'state': state}));

  Future<Json> verification() => _send(() => _dio.get('/me/verification'));

  Future<Json> applications() => _send(() => _dio.get('/me/applications'));

  Future<Json> schemePath(Json facts) =>
      _send(() => _dio.post('/scheme-path', data: {'facts': facts}));

  Future<Json> mySchemePath() => _send(() => _dio.get('/me/scheme-path'));

  Future<Json> family() => _send(() => _dio.get('/me/family'));

  Future<String> familyInvite() async =>
      (await _send(() => _dio.post('/me/family/invite')))['code'] as String;

  Future<void> acceptFamilyInvite(String code) =>
      _send(() => _dio.post('/me/family/accept', data: {'code': code}));

  Future<void> endFamilyLink(String linkId) => _call(() => _dio.delete('/me/family/$linkId'));

  /// Uploads a photo of a Document with the text the phone read from it.
  Future<Json> uploadDocument({
    required String kind,
    required String path,
    required String contentType,
    required String text,
  }) async {
    final form = FormData.fromMap({
      'kind': kind,
      'text': text,
      'file': await MultipartFile.fromFile(
        path,
        filename: path.split('/').last,
        contentType: DioMediaType.parse(contentType),
      ),
    });
    return _send(
      () => _dio.post(
        '/me/documents/uploads',
        data: form,
        options: Options(sendTimeout: const Duration(minutes: 2)),
      ),
    );
  }

  Future<List<dynamic>> uploads() => _sendList(() => _dio.get('/me/documents/uploads'));

  /// The photo itself, fetched through a link that expires in minutes. It is never cached.
  Future<Uint8List> uploadPhoto(String id) async {
    final link = await _send(() => _dio.get('/me/documents/uploads/$id/link'));
    final path = (link['url'] as String).replaceFirst('/v1', '');
    final bytes = await _call(
      () => _dio.get<List<int>>(path, options: Options(responseType: ResponseType.bytes)),
    );
    return Uint8List.fromList(bytes as List<int>);
  }

  Future<void> deleteUpload(String id) => _call(() => _dio.delete('/me/documents/uploads/$id'));

  Future<Json> letter(String kind, String language, Map<String, String> context) => _send(
    () => _dio.get('/me/letters/$kind', queryParameters: {'language': language, ...context}),
  );

  /// The signed-in account's facilitator registration, or null if they have none.
  Future<Json?> facilitator() async {
    final data = await _call(() => _dio.get('/me/facilitator'));
    return data is Json ? data : null;
  }

  Future<Json> registerFacilitator(Json details) =>
      _send(() => _dio.post('/me/facilitator', data: details));

  Future<List<dynamic>> helpedStudents(String language) => _sendList(
    () => _dio.get('/me/facilitator/students', queryParameters: {'language': language}),
  );

  /// Returns the consent code only on a demo deployment, for the synthetic demo numbers.
  Future<String?> requestConsent(String phone) async =>
      (await _send(
            () => _dio.post('/me/facilitator/students', data: {'phone': phone}),
          ))['demo_code']
          as String?;

  Future<void> confirmConsent(String phone, String code) => _send(
    () => _dio.post('/me/facilitator/students/confirm', data: {'phone': phone, 'code': code}),
  );

  Future<Json> answerFor(String studentId, Json facts, String language) => _send(
    () => _dio.post(
      '/me/facilitator/students/$studentId/answers',
      data: {'facts': facts},
      queryParameters: {'language': language},
    ),
  );

  Future<List<dynamic>> helpers() => _sendList(() => _dio.get('/me/helpers'));

  Future<void> removeHelper(String linkId) => _call(() => _dio.delete('/me/helpers/$linkId'));

  /// A room to talk to JAGO in, with the token to join it.
  Future<Json> voiceSession(String language) =>
      _send(() => _dio.post('/me/voice/session', data: {'language': language}));

  Future<Json> grievances() => _send(() => _dio.get('/me/grievances'));

  Future<Json> fileGrievance(String key, String note) =>
      _send(() => _dio.post('/me/grievances', data: {'key': key, 'note': note}));

  Future<List<dynamic>> renewals() => _sendList(() => _dio.get('/me/renewals'));

  Future<List<dynamic>> reminders() => _sendList(() => _dio.get('/me/nudges'));

  Future<List<dynamic>> jagoConversation() => _sendList(() => _dio.get('/me/jago'));

  Future<Json> talkToJago(String message, String language) =>
      _send(() => _dio.post('/me/jago', data: {'message': message, 'language': language}));

  Future<void> verifyInstitution(String code) =>
      _sendList(() => _dio.post('/me/verifications/institution', data: {'code': code}));

  Future<void> verifyNet(String rollNumber) =>
      _sendList(() => _dio.post('/me/verifications/net', data: {'roll_number': rollNumber}));

  Future<void> verifyBank() => _sendList(() => _dio.post('/me/verifications/bank'));

  Future<List<Institute>> searchTopClass(String query) async {
    final json = await _sendList(
      () => _dio.get('/institutes/top-class', queryParameters: {'q': query, 'limit': 30}),
    );
    return [for (final item in json) Institute.fromJson(item as Json)];
  }

  Future<Json> _send(Future<Response<dynamic>> Function() request) async {
    final data = await _call(request);
    return data is Json ? data : <String, dynamic>{};
  }

  Future<List<dynamic>> _sendList(Future<Response<dynamic>> Function() request) async =>
      await _call(request) as List<dynamic>;

  Future<dynamic> _call(Future<Response<dynamic>> Function() request) async {
    try {
      return (await request()).data;
    } on DioException catch (error) {
      throw _translate(error);
    }
  }

  static ApiException _translate(DioException error) {
    final response = error.response;
    if (response == null) {
      return const ApiException('offline', isOffline: true);
    }
    final detail = response.data is Map ? (response.data as Map)['detail'] : null;
    return ApiException(
      detail is String ? detail : 'Something went wrong (${response.statusCode}).',
      statusCode: response.statusCode,
    );
  }

  Future<void> _attachToken(RequestOptions options, RequestInterceptorHandler handler) async {
    if (options.path.startsWith('/me/')) {
      final token = await _tokens.accessToken();
      if (token != null) options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }

  Future<void> _refreshOnUnauthorised(DioException error, ErrorInterceptorHandler handler) async {
    final request = error.requestOptions;
    final unauthorised = error.response?.statusCode == 401;
    if (!unauthorised || !request.path.startsWith('/me/') || request.extra['retried'] == true) {
      return handler.next(error);
    }
    final refresh = await _tokens.refreshToken();
    if (refresh == null) return handler.next(error);
    try {
      final response = await Dio(
        BaseOptions(baseUrl: _dio.options.baseUrl),
      ).post('/auth/refresh', data: {'refresh_token': refresh});
      final json = response.data as Json;
      await _tokens.save(
        access: json['access_token'] as String,
        refresh: json['refresh_token'] as String,
      );
      request.extra['retried'] = true;
      request.headers['Authorization'] = 'Bearer ${json['access_token']}';
      handler.resolve(await _dio.fetch(request));
    } on DioException catch (refreshError) {
      if (refreshError.response?.statusCode == 401) {
        await _tokens.clear();
        onSignedOut?.call();
      }
      handler.next(error);
    }
  }
}
