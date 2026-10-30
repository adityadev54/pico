import AppKit

// Use a native character-only window; never composite GIFs into Tk.
final class CharacterView: NSImageView {
    override func mouseDown(with event: NSEvent) { window?.performDrag(with: event) }
    override func rightMouseDown(with event: NSEvent) {
        if let menu = menu { NSMenu.popUpContextMenu(menu, with: event, for: self) }
    }
}

final class PicoOverlay: NSObject, NSApplicationDelegate {
    var window: NSWindow!
    let image = CharacterView()
    let assets = URL(fileURLWithPath: CommandLine.arguments.dropFirst().first ?? ".")
    var pairing: NSWindow?
    let code = NSTextField()
    let message = NSTextField(wrappingLabelWithString: "")
    let connect = NSButton(title: "Connect", target: nil, action: nil)
    lazy var panels = CompanionPanels(emit: { [weak self] value in self?.emit(value) })
    let reply = PicoReplyBubble(frame: .zero)
    var replyText = "", replyPlace = ""
    var replyTimer: Timer?
    var mood = "idle"
    var character = "tuck"
    var size = "medium"
    func applicationDidFinishLaunching(_ notification: Notification) {
        NSApp.setActivationPolicy(.accessory)
        let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 900, height: 600)
        window = NSWindow(contentRect: NSRect(x: screen.maxX - 200, y: screen.minY + 16, width: 200, height: 250), styleMask: .borderless, backing: .buffered, defer: false)
        window.isOpaque = false
        window.backgroundColor = .clear
        window.hasShadow = false
        window.level = .floating
        window.collectionBehavior = [.canJoinAllSpaces, .fullScreenAuxiliary]
        let content = NSView(frame: NSRect(x: 0, y: 0, width: 200, height: 250))
        content.wantsLayer = true
        content.layer?.backgroundColor = NSColor.clear.cgColor
        image.imageScaling = .scaleProportionallyUpOrDown
        image.animates = true
        image.setAccessibilityLabel("Pico companion")
        content.addSubview(image)
        reply.isHidden = true
        reply.onOpen = { [weak self] in
            guard let self = self, !self.replyPlace.isEmpty else { return }
            self.emit(["action":"open_place","id":self.replyPlace])
        }
        content.addSubview(reply)
        window.contentView = content
        let menu = NSMenu()
        for (title, action) in [("Open apps…", "applications"), ("Permissions…", "permissions"), ("Parked Places", "parked"), ("Unpair…", "unpair"), ("Quit Pico", "quit")] {
            let item = NSMenuItem(title: title, action: #selector(selectAction(_:)), keyEquivalent: "")
            item.target = self; item.representedObject = action; menu.addItem(item)
        }
        image.menu = menu
        update([:])
        window.orderFrontRegardless()
        // The Python worker owns networking and persistence. Only presentation crosses this pipe.
        DispatchQueue.global(qos: .utility).async { [weak self] in
            while let line = readLine() {
                guard let data = line.data(using: .utf8), let value = try? JSONSerialization.jsonObject(with: data) as? [String: String] else { continue }
                DispatchQueue.main.async { self?.update(value) }
            }
            DispatchQueue.main.async { NSApp.terminate(nil) }
        }
        if CommandLine.arguments.contains("--verify") {
            let proof: [String: Any] = ["opaque":window.isOpaque,"shadow":window.hasShadow,"background_alpha":window.backgroundColor.alphaComponent,"image_width":image.frame.width,"window_width":window.frame.width,"animated":image.animates]
            if let data = try? JSONSerialization.data(withJSONObject: proof), let text = String(data: data, encoding: .utf8) { print(text); fflush(stdout) }
        }
    }
    func update(_ value: [String: String]) {
        if let command = value["command"], ["permissions","applications","welcome","notice","approval"].contains(command) { panels.handle(command,payload:value["payload"] ?? "{}");return }
        if value["command"] == "pairing" { showPairing(); return }
        if value["command"] == "pair_status" {
            message.stringValue = value["message"] ?? ""
            connect.isEnabled = value["busy"] != "true"
            return
        }
        if value["command"] == "paired" { pairing?.close(); pairing = nil; return }
        if value["command"] == "dismiss_reply" { reply.isHidden = true; replyText = ""; replyTimer?.invalidate(); return }
        if value["command"] == "reply", let text = value["text"], !text.isEmpty {
            replyText = text; replyPlace = value["place_id"] ?? ""
            reply.isHidden = false
            replyTimer?.invalidate()
            replyTimer = Timer.scheduledTimer(withTimeInterval: 12, repeats: false) { [weak self] _ in
                guard let self = self else { return }
                self.reply.isHidden = true; self.replyText = ""
                if self.mood == "talking" { self.update(["mood":"idle"]) }
            }
        }
        let requested = value["character"] ?? character
        let selected = ["tuck", "mica"].contains(requested) ? requested : "tuck"
        let scale = value["size"] ?? size
        guard ["tuck", "mica"].contains(selected), ["small", "medium", "large"].contains(scale) else { return }
        let activity = value["mood"] ?? mood
        if activity == "idle" && replyPlace.isEmpty { reply.isHidden = true; replyText = "" }
        guard ["idle","listening","talking","working","thinking","done","stuck","needsYou"].contains(activity) else { return }
        let reduced = NSWorkspace.shared.accessibilityDisplayShouldReduceMotion
        let url = assets.appendingPathComponent(selected).appendingPathComponent(activity + (reduced ? ".png" : ".gif"))
        guard let picture = NSImage(contentsOf: url) else { return }
        character = selected; size = scale; mood = activity
        let side: CGFloat = scale == "small" ? 138 : scale == "large" ? 224 : 180
        let width = max(side + 20, 280)
        let old = window.frame
        window.setFrame(NSRect(x: old.maxX - width, y: old.minY, width: width, height: side + 100), display: true)
        image.frame = NSRect(x: (width - side) / 2, y: 0, width: side, height: side)
        if !replyText.isEmpty { reply.update(replyText, mood: mood, width: width, bottom: side + 12) }
        image.setAccessibilityLabel("Pico companion, \(selected), \(activity)")
        image.animates = !reduced
        image.wantsLayer = true
        NSAnimationContext.runAnimationGroup { context in
            context.duration = NSWorkspace.shared.accessibilityDisplayShouldReduceMotion ? 0 : 0.18
            context.allowsImplicitAnimation = true
            image.image = picture
        }
        if CommandLine.arguments.contains("--verify") {
            emit(["rendered_character":selected,"size":scale,"asset_exists":true,"mood":activity,"reply_visible":!reply.isHidden,"reply_above":reply.frame.minY >= image.frame.maxY + 12,"reply_centered":abs(reply.frame.midX - image.frame.midX) < 0.5])
        }
    }
    func showPairing() {
        if let pairing = pairing { pairing.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps: true); return }
        let panel = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 380, height: 270), styleMask: [.titled, .closable], backing: .buffered, defer: false)
        panel.title = "Pico"; panel.isReleasedWhenClosed = false; panel.center()
        let title = NSTextField(labelWithString: "Connect your companion")
        title.font = .systemFont(ofSize: 23, weight: .semibold)
        title.frame = NSRect(x: 24, y: 205, width: 335, height: 32)
        let hint = NSTextField(wrappingLabelWithString: "Enter the code from Pico on your phone.")
        hint.frame = NSRect(x: 24, y: 161, width: 335, height: 36)
        code.frame = NSRect(x: 24, y: 112, width: 332, height: 34)
        code.placeholderString = "Connection code"
        code.font = .monospacedSystemFont(ofSize: 20, weight: .medium)
        code.setAccessibilityLabel("Connection code")
        connect.frame = NSRect(x: 238, y: 65, width: 120, height: 34)
        connect.bezelStyle = .rounded; connect.target = self; connect.action = #selector(pair); connect.keyEquivalent = "\r"
        connect.isEnabled = true
        message.stringValue = ""
        message.frame = NSRect(x: 24, y: 14, width: 332, height: 45)
        message.textColor = .secondaryLabelColor; message.font = .systemFont(ofSize: 12)
        message.maximumNumberOfLines = 3
        for view in [title, hint, code, connect, message] { panel.contentView?.addSubview(view) }
        pairing = panel; panel.makeKeyAndOrderFront(nil); panel.makeFirstResponder(code)
        NSApp.activate(ignoringOtherApps: true)
    }
    @objc func pair() {
        let value = code.stringValue.trimmingCharacters(in: .whitespacesAndNewlines)
        guard value.count == 6 && value.allSatisfy({ $0.isASCII && $0.isNumber }) else {
            message.stringValue = "Enter the six-digit code from your phone."; return
        }
        connect.isEnabled = false; message.stringValue = "Connecting…"
        if let data = try? JSONSerialization.data(withJSONObject: ["action":"pair", "code":value]), let text = String(data: data, encoding: .utf8) {
            print(text); fflush(stdout)
        }
    }
    func emit(_ value:[String:Any]) { if let data = try? JSONSerialization.data(withJSONObject:value),let line = String(data:data,encoding:.utf8) { print(line);fflush(stdout) } }
    @objc func selectAction(_ item: NSMenuItem) {
        guard let action = item.representedObject as? String else { return }
        if action == "unpair" {
            let alert = NSAlert();alert.messageText = "Unpair this computer?";alert.addButton(withTitle:"Keep connected");alert.addButton(withTitle:"Unpair")
            guard alert.runModal() == .alertSecondButtonReturn else{return}
        }
        print(action); fflush(stdout)
    }
}

@main struct Launcher { static func main() {let app = NSApplication.shared;let delegate = PicoOverlay();app.delegate = delegate;app.run()} }
