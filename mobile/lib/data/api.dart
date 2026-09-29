import 'dart:async';

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
  const OtpRequested({required this.phone, required this.resendAfter});

  final String phone;
  final int resendAfter;
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
    return OtpRequested(phone: json['phone'] as String, resendAfter: json['resend_after'] as int);
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
