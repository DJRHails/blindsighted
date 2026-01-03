import { StatusBar } from 'expo-status-bar';
import { StyleSheet, Text, View, Button, Alert, ScrollView } from 'react-native';
import { useEffect, useState, useRef } from 'react';
import * as MetaWearables from 'expo-meta-wearables';
import { videoStreamService } from './src/services/videoStream';
import { META_APP_ID, STREAM_INTERVAL_MS, STREAM_IMAGE_QUALITY, STREAMED_FPS } from './src/config/constants';
import { useDebounce } from './src/hooks';

export default function App() {
  const [isConnected, setIsConnected] = useState(false);
  const [deviceInfo, setDeviceInfo] = useState<any>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isInitialized, setIsInitialized] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [lastDescription, setLastDescription] = useState<string>('');
  const streamIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Debounce the description to prevent rapid UI updates
  const debouncedDescription = useDebounce(lastDescription, 300);

  useEffect(() => {
    initializeSDK();
  }, []);

  const initializeSDK = async () => {
    try {
      await MetaWearables.initialize({
        appId: META_APP_ID,
        analyticsEnabled: false,
      });
      setIsInitialized(true);

      const connectionSub = MetaWearables.addConnectionListener((event) => {
        console.log('Connection event:', event);
        setIsConnected(event.status === 'connected');
        setDeviceInfo(event.device);
      });

      const recordingSub = MetaWearables.addRecordingListener((event) => {
        console.log('Recording event:', event);
        setIsRecording(event.isRecording);
      });

      return () => {
        connectionSub.remove();
        recordingSub.remove();
      };
    } catch (error) {
      Alert.alert('Initialization Error', String(error));
    }
  };

  const handleConnect = async () => {
    try {
      await MetaWearables.connectDevice();
    } catch (error) {
      Alert.alert('Connection Error', String(error));
    }
  };

  const handleDisconnect = async () => {
    try {
      await MetaWearables.disconnectDevice();
    } catch (error) {
      Alert.alert('Disconnect Error', String(error));
    }
  };

  const handleCapturePhoto = async () => {
    try {
      const result = await MetaWearables.capturePhoto({ quality: 90 });
      Alert.alert('Photo Captured', `URI: ${result.uri}\nSize: ${result.width}x${result.height}`);
    } catch (error) {
      Alert.alert('Photo Capture Error', String(error));
    }
  };

  const handleStartRecording = async () => {
    try {
      await MetaWearables.startVideoRecording({
        quality: 'high',
        maxDuration: 30,
      });
    } catch (error) {
      Alert.alert('Recording Error', String(error));
    }
  };

  const handleStopRecording = async () => {
    try {
      const result = await MetaWearables.stopVideoRecording();
      Alert.alert(
        'Video Recorded',
        `URI: ${result.uri}\nDuration: ${result.duration}s`
      );
    } catch (error) {
      Alert.alert('Stop Recording Error', String(error));
    }
  };

  const handleStartStreaming = async () => {
    try {
      await videoStreamService.startStreaming((frameData) => {
        console.log('Frame captured at:', new Date(frameData.timestamp));
      });
      setIsStreaming(true);

      // Capture frames at configured FPS
      streamIntervalRef.current = setInterval(async () => {
        try {
          const photo = await MetaWearables.capturePhoto({ quality: STREAM_IMAGE_QUALITY });
          const result = await videoStreamService.captureAndSendFrame(photo.uri);

          // Update UI with description
          if (result && result.description) {
            setLastDescription(result.description);
          }
        } catch (error) {
          console.error('Error capturing frame:', error);
        }
      }, STREAM_INTERVAL_MS);
    } catch (error) {
      Alert.alert('Streaming Error', String(error));
    }
  };

  const handleStopStreaming = () => {
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }
    videoStreamService.stopStreaming();
    setIsStreaming(false);
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      handleStopStreaming();
    };
  }, []);

  return (
    <View style={styles.container}>
      <StatusBar style="auto" />
      <ScrollView style={styles.scrollView} contentContainerStyle={styles.content}>
        <Text style={styles.title}>Blindsighted</Text>
        <Text style={styles.subtitle}>Meta AI Glasses Integration</Text>

        <View style={styles.statusCard}>
          <Text style={styles.statusLabel}>SDK Status:</Text>
          <Text style={styles.statusValue}>{isInitialized ? 'Initialized' : 'Not Initialized'}</Text>

          <Text style={styles.statusLabel}>Connection:</Text>
          <Text style={[styles.statusValue, isConnected && styles.connected]}>
            {isConnected ? 'Connected' : 'Disconnected'}
          </Text>

          {deviceInfo && (
            <>
              <Text style={styles.statusLabel}>Device Model:</Text>
              <Text style={styles.statusValue}>{deviceInfo.model}</Text>

              <Text style={styles.statusLabel}>Battery:</Text>
              <Text style={styles.statusValue}>{deviceInfo.batteryLevel}%</Text>

              <Text style={styles.statusLabel}>Firmware:</Text>
              <Text style={styles.statusValue}>{deviceInfo.firmwareVersion}</Text>
            </>
          )}

          <Text style={styles.statusLabel}>Recording:</Text>
          <Text style={[styles.statusValue, isRecording && styles.recording]}>
            {isRecording ? 'Yes' : 'No'}
          </Text>

          <Text style={styles.statusLabel}>Streaming:</Text>
          <Text style={[styles.statusValue, isStreaming && styles.streaming]}>
            {isStreaming ? `Active (${STREAMED_FPS} FPS)` : 'Inactive'}
          </Text>

          {debouncedDescription && (
            <>
              <Text style={styles.statusLabel}>Last Description:</Text>
              <Text style={styles.statusValue}>{debouncedDescription}</Text>
            </>
          )}
        </View>

        <View style={styles.buttonContainer}>
          <Button
            title={isConnected ? 'Disconnect Device' : 'Connect Device'}
            onPress={isConnected ? handleDisconnect : handleConnect}
            disabled={!isInitialized}
          />

          <View style={styles.spacer} />

          <Button
            title="Capture Photo"
            onPress={handleCapturePhoto}
            disabled={!isConnected}
          />

          <View style={styles.spacer} />

          <Button
            title={isRecording ? 'Stop Recording' : 'Start Recording'}
            onPress={isRecording ? handleStopRecording : handleStartRecording}
            disabled={!isConnected}
          />

          <View style={styles.spacer} />

          <Button
            title={isStreaming ? 'Stop AI Streaming' : 'Start AI Streaming'}
            onPress={isStreaming ? handleStopStreaming : handleStartStreaming}
            disabled={!isConnected}
            color={isStreaming ? '#f44336' : '#2196F3'}
          />
        </View>

        <Text style={styles.note}>
          Note: This demo uses the expo-meta-wearables package.
          {'\n'}Use a debug build with Mock Device Kit for testing without hardware.
        </Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  scrollView: {
    flex: 1,
  },
  content: {
    padding: 20,
    paddingTop: 60,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    color: '#666',
    marginBottom: 30,
  },
  statusCard: {
    backgroundColor: '#fff',
    padding: 20,
    borderRadius: 12,
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#666',
    marginTop: 12,
  },
  statusValue: {
    fontSize: 16,
    color: '#333',
    marginTop: 4,
  },
  connected: {
    color: '#4CAF50',
    fontWeight: '600',
  },
  recording: {
    color: '#f44336',
    fontWeight: '600',
  },
  streaming: {
    color: '#2196F3',
    fontWeight: '600',
  },
  buttonContainer: {
    marginBottom: 24,
  },
  spacer: {
    height: 12,
  },
  note: {
    fontSize: 12,
    color: '#999',
    textAlign: 'center',
    fontStyle: 'italic',
    marginTop: 20,
  },
});
