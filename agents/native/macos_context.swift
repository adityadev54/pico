import AppKit
import CoreGraphics
import ImageIO
import UniformTypeIdentifiers

var result: [String: Any] = ["idle": CGEventSource.secondsSinceLastEventType(.combinedSessionState, eventType: .null), "screen_access": CGPreflightScreenCaptureAccess()]
if let app = NSWorkspace.shared.frontmostApplication {
    result["app"] = app.localizedName ?? "Unknown app"
    result["bundle"] = app.bundleIdentifier ?? ""
    if let windows = CGWindowListCopyWindowInfo([.optionOnScreenOnly, .excludeDesktopElements], kCGNullWindowID) as? [[String: Any]],
       let window = windows.first(where: { ($0[kCGWindowOwnerPID as String] as? Int32) == app.processIdentifier && ($0[kCGWindowLayer as String] as? Int) == 0 }) {
        result["title"] = window[kCGWindowName as String] as? String ?? ""
        // Capture only this active app window, never the full display.
        if CommandLine.arguments.count == 3 && CommandLine.arguments[1] == "snapshot", CGPreflightScreenCaptureAccess(),
           let id = window[kCGWindowNumber as String] as? UInt32,
           let image = CGWindowListCreateImage(.null, .optionIncludingWindow, id, [.boundsIgnoreFraming, .bestResolution]) {
            let width = min(image.width, 1280)
            let height = max(1, Int(Double(image.height) * Double(width) / Double(image.width)))
            if let context = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0, space: CGColorSpaceCreateDeviceRGB(), bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) {
                context.interpolationQuality = .high
                context.draw(image, in: CGRect(x: 0, y: 0, width: width, height: height))
                if let scaled = context.makeImage(), let out = CGImageDestinationCreateWithURL(URL(fileURLWithPath: CommandLine.arguments[2]) as CFURL, UTType.png.identifier as CFString, 1, nil) {
                    CGImageDestinationAddImage(out, scaled, nil)
                    result["snapshot_saved"] = CGImageDestinationFinalize(out)
                }
            }
        }
    }
}
if CommandLine.arguments.contains("request-screen-access") { result["screen_access"] = CGRequestScreenCaptureAccess() }
let data = try JSONSerialization.data(withJSONObject: result)
FileHandle.standardOutput.write(data)
