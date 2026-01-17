import Foundation

/// Request to start a streaming session
struct StartSessionRequest: Codable {
    let userId: String?
    let deviceId: String?
    let agentId: String?

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case deviceId = "device_id"
        case agentId = "agent_id"
    }

    init(userId: String? = nil, deviceId: String? = nil, agentId: String? = nil) {
        self.userId = userId
        self.deviceId = deviceId
        self.agentId = agentId
    }
}

/// Response from /sessions/start endpoint
struct StartSessionResponse: Codable {
    let sessionId: String  // UUID serialized as string
    let roomName: String
    let token: String
    let livekitUrl: String

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case roomName = "room_name"
        case token
        case livekitUrl = "livekit_url"
    }
}

/// Request to stop a streaming session
struct StopSessionRequest: Codable {
    let sessionId: String  // UUID serialized as string

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
    }
}

/// Response from /sessions/stop endpoint
struct StopSessionResponse: Codable {
    let message: String
}

/// Error response from API
struct APIErrorResponse: Codable {
    let detail: String
}

/// Errors from API client
enum APIClientError: Error, LocalizedError {
    case invalidURL
    case requestFailed(String)
    case decodingFailed
    case networkError(Error)
    case serverError(Int, String)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid API URL"
        case .requestFailed(let message):
            return "Request failed: \(message)"
        case .decodingFailed:
            return "Failed to decode response"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .serverError(let code, let message):
            return "Server error (\(code)): \(message)"
        }
    }
}

/// Client for communicating with the Blindsighted FastAPI backend
@MainActor
class APIClient: ObservableObject {
    private let baseURL: String
    private let session: URLSession

    init(baseURL: String) {
        // Ensure base URL doesn't have trailing slash
        self.baseURL = baseURL.trimmingCharacters(in: CharacterSet(charactersIn: "/"))

        // Configure URLSession with timeout
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForRequest = 30
        config.timeoutIntervalForResource = 60
        self.session = URLSession(configuration: config)
    }

    // MARK: - Session Management

    /// Start a new streaming session and get LiveKit credentials
    func startSession(userId: String? = nil, deviceId: String? = nil, agentId: String? = nil) async throws -> StartSessionResponse {
        let request = StartSessionRequest(userId: userId, deviceId: deviceId, agentId: agentId)
        return try await post(endpoint: "/sessions/start", body: request)
    }

    /// Stop an active streaming session
    func stopSession(sessionId: String) async throws -> StopSessionResponse {
        let request = StopSessionRequest(sessionId: sessionId)
        return try await post(endpoint: "/sessions/stop", body: request)
    }

    // MARK: - HTTP Methods

    private func post<T: Encodable, R: Decodable>(endpoint: String, body: T) async throws -> R {
        guard let url = URL(string: "\(baseURL)\(endpoint)") else {
            throw APIClientError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Encode request body
        let encoder = JSONEncoder()
        request.httpBody = try encoder.encode(body)

        // Make request
        let (data, response) = try await session.data(for: request)

        // Check HTTP status
        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIClientError.requestFailed("Invalid response type")
        }

        // Handle error status codes
        if httpResponse.statusCode >= 400 {
            let errorMessage: String
            if let apiError = try? JSONDecoder().decode(APIErrorResponse.self, from: data) {
                errorMessage = apiError.detail
            } else {
                errorMessage = HTTPURLResponse.localizedString(forStatusCode: httpResponse.statusCode)
            }
            throw APIClientError.serverError(httpResponse.statusCode, errorMessage)
        }

        // Decode response
        let decoder = JSONDecoder()
        do {
            return try decoder.decode(R.self, from: data)
        } catch {
            NSLog("[APIClient] Decoding error: \(error)")
            NSLog("[APIClient] Response data: \(String(data: data, encoding: .utf8) ?? "nil")")
            throw APIClientError.decodingFailed
        }
    }

    // MARK: - Health Check

    /// Check if the API is reachable
    func checkHealth() async -> Bool {
        guard let url = URL(string: "\(baseURL)/health") else {
            return false
        }

        do {
            let (_, response) = try await session.data(from: url)
            guard let httpResponse = response as? HTTPURLResponse else {
                return false
            }
            return httpResponse.statusCode == 200
        } catch {
            return false
        }
    }
}
