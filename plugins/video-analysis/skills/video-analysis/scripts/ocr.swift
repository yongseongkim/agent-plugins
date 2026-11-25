import Darwin
import Foundation
import Vision

struct OCRFailure: LocalizedError {
    let message: String
    var errorDescription: String? { message }
    init(_ message: String) { self.message = message }
}

func readFrame(_ file: URL, fps: Double, languages: [String]) throws -> Data {
    guard let number = Int(file.deletingPathExtension().lastPathComponent), number > 0 else {
        throw OCRFailure("Expected numbered frames starting at 1: \(file.lastPathComponent)")
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.recognitionLanguages = languages
    request.usesLanguageCorrection = true
    do {
        try VNImageRequestHandler(url: file).perform([request])
    } catch {
        throw OCRFailure("Vision OCR failed on \(file.lastPathComponent): \(error.localizedDescription)")
    }
    let rows: [[String: Any]] = (request.results ?? []).compactMap { observation in
        guard let item = observation.topCandidates(1).first else { return nil }
        let box = observation.boundingBox
        return ["text": item.string, "confidence": item.confidence,
                "x": box.minX, "y": 1 - box.maxY, "width": box.width, "height": box.height]
    }
    // JPEG numbering starts at 1 for a sequence sampled from playback time zero.
    let record: [String: Any] = ["time": Double(number - 1) / fps, "frame": file.lastPathComponent, "lines": rows]
    var data = try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys])
    data.append(10)
    return data
}

func run(_ args: [String]) throws {
    guard args.count == 5, let fps = Double(args[2]), fps.isFinite, fps > 0 else {
        throw OCRFailure("Usage: ocr.swift FRAMES FPS OUTPUT.jsonl ko-KR,en-US")
    }
    let manager = FileManager.default
    let dir = URL(fileURLWithPath: args[1])
    let target = URL(fileURLWithPath: args[3])
    let languages = args[4].split(separator: ",").map(String.init)
    let files = try manager.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
        .filter { $0.pathExtension.lowercased() == "jpg" }
        .sorted { $0.lastPathComponent < $1.lastPathComponent }
    guard !files.isEmpty else { throw OCRFailure("No JPEG frames found") }

    try manager.createDirectory(at: target.deletingLastPathComponent(), withIntermediateDirectories: true)
    let partial = target.appendingPathExtension(UUID().uuidString + ".partial")
    defer { try? manager.removeItem(at: partial) }
    try Data().write(to: partial)
    let handle = try FileHandle(forWritingTo: partial)
    do {
        for file in files {
            try autoreleasepool {
                try handle.write(contentsOf: readFrame(file, fps: fps, languages: languages))
            }
        }
        try handle.close()
    } catch {
        try? handle.close()
        throw error
    }
    if rename(partial.path, target.path) != 0 {
        throw POSIXError(POSIXErrorCode(rawValue: errno) ?? .EIO)
    }
    print("OCR: \(files.count) frames")
}

do {
    try run(CommandLine.arguments)
} catch {
    FileHandle.standardError.write(Data("\(error.localizedDescription)\n".utf8))
    exit(1)
}
