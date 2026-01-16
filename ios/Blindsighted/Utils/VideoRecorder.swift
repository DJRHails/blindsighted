//
// VideoRecorder.swift
//
// Helper class for recording video streams to files using AVAssetWriter.
// Handles video encoding, file management, and frame timing.
//

import AVFoundation
import MWDATCamera
import UIKit

enum VideoRecorderError: Error {
  case writerCreationFailed
  case inputNotReady
  case frameAppendFailed
  case finishWritingFailed
}

@MainActor
class VideoRecorder {
  private var assetWriter: AVAssetWriter?
  private var videoInput: AVAssetWriterInput?
  private var pixelBufferAdaptor: AVAssetWriterInputPixelBufferAdaptor?
  private var isRecording = false
  private var frameCount: Int64 = 0
  private var startTime: CMTime?
  private let outputURL: URL
  private let videoSize: CGSize
  private let frameRate: Int32

  init(outputURL: URL, videoSize: CGSize = CGSize(width: 1280, height: 720), frameRate: Int32 = 24) {
    self.outputURL = outputURL
    self.videoSize = videoSize
    self.frameRate = frameRate
  }

  func startRecording() throws {
    // Remove existing file if present
    try? FileManager.default.removeItem(at: outputURL)

    // Create asset writer
    guard let writer = try? AVAssetWriter(outputURL: outputURL, fileType: .mp4) else {
      throw VideoRecorderError.writerCreationFailed
    }

    // Configure video settings
    let videoSettings: [String: Any] = [
      AVVideoCodecKey: AVVideoCodecType.h264,
      AVVideoWidthKey: videoSize.width,
      AVVideoHeightKey: videoSize.height,
      AVVideoCompressionPropertiesKey: [
        AVVideoAverageBitRateKey: 6_000_000,
        AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
      ],
    ]

    // Create video input
    let input = AVAssetWriterInput(mediaType: .video, outputSettings: videoSettings)
    input.expectsMediaDataInRealTime = true

    // Create pixel buffer adaptor
    let sourcePixelBufferAttributes: [String: Any] = [
      kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32ARGB,
      kCVPixelBufferWidthKey as String: videoSize.width,
      kCVPixelBufferHeightKey as String: videoSize.height,
    ]

    let adaptor = AVAssetWriterInputPixelBufferAdaptor(
      assetWriterInput: input,
      sourcePixelBufferAttributes: sourcePixelBufferAttributes
    )

    guard writer.canAdd(input) else {
      throw VideoRecorderError.inputNotReady
    }

    writer.add(input)

    self.assetWriter = writer
    self.videoInput = input
    self.pixelBufferAdaptor = adaptor
    self.frameCount = 0
    self.startTime = nil

    guard writer.startWriting() else {
      throw VideoRecorderError.writerCreationFailed
    }

    writer.startSession(atSourceTime: .zero)
    isRecording = true
  }

  func appendFrame(_ videoFrame: VideoFrame) throws {
    guard isRecording,
          let input = videoInput,
          let adaptor = pixelBufferAdaptor,
          input.isReadyForMoreMediaData else {
      return
    }

    // Convert VideoFrame to CVPixelBuffer with the configured video size
    guard let pixelBuffer = videoFrame.makePixelBuffer(targetSize: videoSize) else {
      throw VideoRecorderError.frameAppendFailed
    }

    // Calculate presentation time
    let presentationTime = CMTime(value: frameCount, timescale: frameRate)

    // Append the pixel buffer
    guard adaptor.append(pixelBuffer, withPresentationTime: presentationTime) else {
      throw VideoRecorderError.frameAppendFailed
    }

    frameCount += 1
  }

  func stopRecording() async throws -> URL {
    guard isRecording else {
      return outputURL
    }

    isRecording = false

    guard let writer = assetWriter, let input = videoInput else {
      throw VideoRecorderError.writerCreationFailed
    }

    input.markAsFinished()

    await writer.finishWriting()

    guard writer.status == .completed else {
      throw VideoRecorderError.finishWritingFailed
    }

    return outputURL
  }

  var recordingDuration: TimeInterval {
    guard frameCount > 0 else { return 0 }
    return Double(frameCount) / Double(frameRate)
  }
}

extension VideoFrame {
  /// Convert VideoFrame to CVPixelBuffer for video recording with specific size
  func makePixelBuffer(targetSize: CGSize) -> CVPixelBuffer? {
    // Convert to UIImage first, then to CVPixelBuffer
    guard let uiImage = makeUIImage() else {
      return nil
    }

    return uiImage.pixelBuffer(targetSize: targetSize)
  }
}

extension UIImage {
  /// Convert UIImage to CVPixelBuffer with specific target size
  func pixelBuffer(targetSize: CGSize) -> CVPixelBuffer? {
    let width = Int(targetSize.width)
    let height = Int(targetSize.height)

    let attributes: [String: Any] = [
      kCVPixelBufferCGImageCompatibilityKey as String: true,
      kCVPixelBufferCGBitmapContextCompatibilityKey as String: true,
    ]

    var pixelBuffer: CVPixelBuffer?
    let status = CVPixelBufferCreate(
      kCFAllocatorDefault,
      width,
      height,
      kCVPixelFormatType_32ARGB,
      attributes as CFDictionary,
      &pixelBuffer
    )

    guard status == kCVReturnSuccess, let buffer = pixelBuffer else {
      return nil
    }

    CVPixelBufferLockBaseAddress(buffer, [])
    defer { CVPixelBufferUnlockBaseAddress(buffer, []) }

    let pixelData = CVPixelBufferGetBaseAddress(buffer)
    let rgbColorSpace = CGColorSpaceCreateDeviceRGB()

    guard let context = CGContext(
      data: pixelData,
      width: width,
      height: height,
      bitsPerComponent: 8,
      bytesPerRow: CVPixelBufferGetBytesPerRow(buffer),
      space: rgbColorSpace,
      bitmapInfo: CGImageAlphaInfo.noneSkipFirst.rawValue
    ) else {
      return nil
    }

    context.translateBy(x: 0, y: CGFloat(height))
    context.scaleBy(x: 1.0, y: -1.0)

    UIGraphicsPushContext(context)
    draw(in: CGRect(x: 0, y: 0, width: width, height: height))
    UIGraphicsPopContext()

    return buffer
  }
}
