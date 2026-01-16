import SwiftUI

/// Settings view for configuring LiveKit connection
struct LiveKitSettingsView: View {
    @Environment(\.dismiss) private var dismiss

    @State private var mode: LiveKitMode = .api
    @State private var apiURL: String = ""
    @State private var serverURL: String = ""
    @State private var token: String = ""
    @State private var roomName: String = ""
    @State private var enableVideo: Bool = true
    @State private var enableAudio: Bool = true
    @State private var showSaved: Bool = false
    @State private var showError: Bool = false
    @State private var errorMessage: String = ""

    // Callback to notify parent view of config changes
    var onConfigSaved: ((LiveKitConfig) -> Void)?

    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Connection Mode")) {
                    Picker("Mode", selection: $mode) {
                        Text("API (Recommended)").tag(LiveKitMode.api)
                        Text("Manual").tag(LiveKitMode.manual)
                    }
                    .pickerStyle(.segmented)
                }

                if mode == .api {
                    apiModeSection
                } else {
                    manualModeSection
                }

                Section(header: Text("Publishing Options")) {
                    Toggle("Enable Video", isOn: $enableVideo)
                    Toggle("Enable Audio", isOn: $enableAudio)
                }

                Section(header: Text("About")) {
                    VStack(alignment: .leading, spacing: 8) {
                        if mode == .api {
                            Text("API mode fetches tokens automatically from your backend.")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            Text("Deployment options:")
                                .font(.caption)
                                .fontWeight(.semibold)
                                .foregroundColor(.secondary)

                            Text("• Local network: http://YOUR_COMPUTER_IP:8000")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            Text("• ngrok/Cloudflare Tunnel: https://your-url.ngrok.io")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            Text("• Cloud: Deploy to Railway, Fly.io, etc.")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        } else {
                            Text("Manual mode requires you to generate tokens yourself.")
                                .font(.caption)
                                .foregroundColor(.secondary)

                            Text("Get started at livekit.io")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                }

                Section {
                    Button(action: saveConfiguration) {
                        HStack {
                            Spacer()
                            Text("Save Configuration")
                                .fontWeight(.semibold)
                            Spacer()
                        }
                    }
                    .disabled(!isFormValid)

                    Button(action: clearConfiguration) {
                        HStack {
                            Spacer()
                            Text("Clear Configuration")
                                .foregroundColor(.red)
                            Spacer()
                        }
                    }
                }
            }
            .navigationTitle("LiveKit Settings")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
            .alert("Configuration Saved", isPresented: $showSaved) {
                Button("OK") {
                    dismiss()
                }
            } message: {
                Text("Your LiveKit configuration has been saved successfully.")
            }
            .alert("Error", isPresented: $showError) {
                Button("OK") { }
            } message: {
                Text(errorMessage)
            }
            .onAppear {
                loadConfiguration()
            }
        }
    }

    // MARK: - UI Sections

    private var apiModeSection: some View {
        Section(header: Text("API Configuration")) {
            TextField("API URL", text: $apiURL)
                .keyboardType(.URL)
                .autocapitalization(.none)
            Text("Example: http://192.168.1.100:8000")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }

    private var manualModeSection: some View {
        Section(header: Text("Manual Configuration")) {
            TextField("LiveKit Server URL", text: $serverURL)
                .keyboardType(.URL)
                .autocapitalization(.none)

            TextField("Room Name", text: $roomName)

            SecureField("Access Token", text: $token)
        }
    }

    // MARK: - Computed Properties

    private var isFormValid: Bool {
        switch mode {
        case .api:
            return !apiURL.isEmpty
        case .manual:
            return !serverURL.isEmpty && !token.isEmpty && !roomName.isEmpty
        }
    }

    // MARK: - Actions

    private func saveConfiguration() {
        let config: LiveKitConfig

        switch mode {
        case .api:
            // Validate API URL format
            guard let url = URL(string: apiURL), url.scheme == "http" || url.scheme == "https" else {
                errorMessage = "Invalid API URL. Must start with http:// or https://"
                showError = true
                return
            }
            config = .apiMode(apiURL: apiURL, enableVideo: enableVideo, enableAudio: enableAudio)

        case .manual:
            // Validate LiveKit server URL format
            guard let url = URL(string: serverURL), url.scheme == "ws" || url.scheme == "wss" else {
                errorMessage = "Invalid LiveKit URL. Must start with ws:// or wss://"
                showError = true
                return
            }
            config = .manualMode(
                serverURL: serverURL,
                token: token,
                roomName: roomName,
                enableVideo: enableVideo,
                enableAudio: enableAudio
            )
        }

        config.saveToUserDefaults()
        onConfigSaved?(config)
        showSaved = true
    }

    private func clearConfiguration() {
        LiveKitConfig.clearFromUserDefaults()
        apiURL = ""
        serverURL = ""
        token = ""
        roomName = ""
        enableVideo = true
        enableAudio = true
    }

    private func loadConfiguration() {
        if let config = LiveKitConfig.loadFromUserDefaults() {
            mode = config.mode
            apiURL = config.apiURL ?? ""
            serverURL = config.serverURL ?? ""
            token = config.token ?? ""
            roomName = config.roomName ?? ""
            enableVideo = config.enableVideo
            enableAudio = config.enableAudio
        }
    }
}

// MARK: - Preview

struct LiveKitSettingsView_Previews: PreviewProvider {
    static var previews: some View {
        LiveKitSettingsView()
    }
}
