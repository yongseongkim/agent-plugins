import Foundation
import Vision

let args = CommandLine.arguments
guard args.count == 5, let fps = Double(args[2]), fps > 0 else {
    fatalError("Usage: ocr.swift FRAMES FPS OUTPUT.jsonl ko-KR,en-US")
}
let dir = URL(fileURLWithPath: args[1])
let target = URL(fileURLWithPath: args[3])
let languages = args[4].split(separator: ",").map(String.init)
let files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
    .filter { $0.pathExtension.lowercased() == "jpg" }
    .sorted { $0.lastPathComponent < $1.lastPathComponent }
guard !files.isEmpty else { fatalError("No JPEG frames found") }
let partial = target.appendingPathExtension(UUID().uuidString + ".partial")
try Data().write(to: partial)
let handle = try FileHandle(forWritingTo: partial)
for file in files {
    try autoreleasepool {
        guard let n = Int(file.deletingPathExtension().lastPathComponent), n > 0 else {
            fatalError("Expected numbered frames starting at 1")
        }
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = languages
        request.usesLanguageCorrection = true
        do {
            try VNImageRequestHandler(url: file).perform([request])
        } catch {
            FileHandle.standardError.write(Data("Vision OCR failed on \(file.lastPathComponent): \(error.localizedDescription)\n".utf8))
            try? handle.close()
            try? FileManager.default.removeItem(at: partial)
            exit(1)
        }
        let rows: [[String: Any]] = (request.results ?? []).compactMap { observation in
            guard let item = observation.topCandidates(1).first else { return nil }
            let box = observation.boundingBox
            return ["text": item.string, "confidence": item.confidence,
                    "x": box.minX, "y": 1 - box.maxY, "width": box.width, "height": box.height]
        }
        // 0초부터 일정한 간격으로 뽑은 JPEG는 파일 번호가 1부터 시작한다.
        let record: [String: Any] = ["time": Double(n - 1) / fps, "frame": file.lastPathComponent, "lines": rows]
        var data = try JSONSerialization.data(withJSONObject: record, options: [.sortedKeys])
        data.append(10)
        try handle.write(contentsOf: data)
    }
}
try handle.close()
if FileManager.default.fileExists(atPath: target.path) {
    _ = try FileManager.default.replaceItemAt(target, withItemAt: partial)
} else {
    try FileManager.default.moveItem(at: partial, to: target)
}
print("OCR: \(files.count) frames")
