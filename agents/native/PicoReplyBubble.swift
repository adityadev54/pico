import AppKit

/// Pico’s compact companion speech bubble, using system appearance colors.
final class PicoReplyBubble: NSView {
    private let label = NSTextField(wrappingLabelWithString: "")
    private let symbol = NSImageView()
    var onOpen: (() -> Void)?
    override init(frame: NSRect) {
        super.init(frame: frame)
        label.font = .systemFont(ofSize: 12, weight: .medium)
        label.textColor = .labelColor
        label.maximumNumberOfLines = 2
        label.lineBreakMode = .byWordWrapping
        symbol.contentTintColor = .systemRed
        addSubview(symbol); addSubview(label)
        setAccessibilityElement(true); setAccessibilityRole(.button)
    }
    required init?(coder: NSCoder) { fatalError("init(coder:) has not been implemented") }
    override func mouseDown(with event: NSEvent) { onOpen?() }
    override func accessibilityPerformPress() -> Bool { onOpen?(); return onOpen != nil }
    func update(_ text: String, mood: String, width available: CGFloat, bottom: CGFloat) {
        label.stringValue = text; setAccessibilityLabel(text)
        let icon = mood == "working" ? "ellipsis" : mood == "listening" ? "waveform" : "text.bubble"
        symbol.image = NSImage(systemSymbolName: icon, accessibilityDescription: nil)
        let natural = (text as NSString).size(withAttributes: [.font: label.font!]).width
        let width = min(available - 12, max(112, ceil(natural) + 56))
        let textWidth = width - 48
        let measured = label.cell!.cellSize(forBounds: NSRect(x: 0, y: 0, width: textWidth, height: 40))
        let textHeight = min(32, max(16, ceil(measured.height)))
        let bodyHeight = textHeight + 18
        frame = NSRect(x: (available - width) / 2, y: bottom, width: width, height: bodyHeight + 17)
        symbol.frame = NSRect(x: 15, y: 11 + (bodyHeight - 14) / 2, width: 14, height: 14)
        label.frame = NSRect(x: 35, y: 11 + (bodyHeight - textHeight) / 2, width: textWidth, height: textHeight)
        needsDisplay = true
    }
    override func draw(_ dirtyRect: NSRect) {
        let body = bounds.insetBy(dx: 5, dy: 0)
        let left = body.minX, right = body.maxX, bottom: CGFloat = 11, top = bounds.maxY - 6
        let radius: CGFloat = 16, middle = body.midX
        let path = NSBezierPath()
        path.move(to: NSPoint(x: left + radius, y: bottom))
        path.line(to: NSPoint(x: middle - 5, y: bottom))
        path.curve(to: NSPoint(x: middle + 7, y: bottom - 6), controlPoint1: NSPoint(x: middle - 2, y: bottom - 3), controlPoint2: NSPoint(x: middle + 1, y: bottom - 6))
        path.curve(to: NSPoint(x: middle + 5, y: bottom), controlPoint1: NSPoint(x: middle + 5, y: bottom - 4), controlPoint2: NSPoint(x: middle + 5, y: bottom - 2))
        path.line(to: NSPoint(x: right - radius, y: bottom))
        path.curve(to: NSPoint(x: right, y: bottom + radius), controlPoint1: NSPoint(x: right - 7, y: bottom), controlPoint2: NSPoint(x: right, y: bottom + 7))
        path.line(to: NSPoint(x: right, y: top - radius))
        path.curve(to: NSPoint(x: right - radius, y: top), controlPoint1: NSPoint(x: right, y: top - 7), controlPoint2: NSPoint(x: right - 7, y: top))
        path.line(to: NSPoint(x: left + radius, y: top))
        path.curve(to: NSPoint(x: left, y: top - radius), controlPoint1: NSPoint(x: left + 7, y: top), controlPoint2: NSPoint(x: left, y: top - 7))
        path.line(to: NSPoint(x: left, y: bottom + radius))
        path.curve(to: NSPoint(x: left + radius, y: bottom), controlPoint1: NSPoint(x: left, y: bottom + 7), controlPoint2: NSPoint(x: left + 7, y: bottom))
        path.close()
        NSGraphicsContext.saveGraphicsState()
        let shadow = NSShadow(); shadow.shadowColor = NSColor.black.withAlphaComponent(0.12)
        shadow.shadowBlurRadius = 5; shadow.shadowOffset = NSSize(width: 0, height: -1); shadow.set()
        NSColor.controlBackgroundColor.setFill(); path.fill()
        NSGraphicsContext.restoreGraphicsState()
        NSColor.separatorColor.withAlphaComponent(0.25).setStroke(); path.lineWidth = 0.6; path.stroke()
    }
}
