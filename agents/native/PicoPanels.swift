import AppKit
import UniformTypeIdentifiers
import CoreGraphics

final class TopAlignedClipView: NSClipView { override var isFlipped: Bool { true } }

/// Companion panels use native semantic colors and AppKit controls in both appearances.
final class CompanionPanels: NSObject {
    let emit: ([String:Any])->Void
    var applications: NSWindow?
    var permissions: NSWindow?
    var welcome: NSWindow?
    var settings: [String:Any] = [:]
    var permissionGroups:[NSBox] = []
    var preferencesStack: NSStackView?
    var currentID = ""
    var currentText = ""
    init(emit: @escaping ([String:Any])->Void) { self.emit = emit }
    func label(_ text: String, size: CGFloat = 13, bold: Bool = false) -> NSTextField {
        let view = NSTextField(wrappingLabelWithString: text)
        view.font = .systemFont(ofSize: size, weight: bold ? .semibold : .regular)
        view.textColor = .labelColor
        return view
    }
    func stack(_ views:[NSView], vertical:Bool = true, spacing:CGFloat = 12) -> NSStackView {
        views.forEach { $0.translatesAutoresizingMaskIntoConstraints = false }
        let result = NSStackView(views:views); result.orientation = vertical ? .vertical : .horizontal
        result.alignment = vertical ? .leading : .centerY; result.spacing = spacing
        if !vertical { result.distribution = .fill }
        return result
    }
    func button(_ title:String, _ action:Selector) -> NSButton {
        let b = NSButton(title:title,target:self,action:action);b.bezelStyle = .rounded;return b
    }
    func panel(_ title:String, width:CGFloat, height:CGFloat) -> NSWindow {
        let w = NSWindow(contentRect:NSRect(x:0,y:0,width:width,height:height),styleMask:[.titled,.closable],backing:.buffered,defer:false)
        w.title = title; w.isReleasedWhenClosed = false; w.center()
        return w
    }
    func mount(_ content:NSView, in window:NSWindow, inset:CGFloat = 24) {
        guard let host = window.contentView else {return}
        host.subviews.forEach{$0.removeFromSuperview()};content.translatesAutoresizingMaskIntoConstraints = false;host.addSubview(content)
        NSLayoutConstraint.activate([content.leadingAnchor.constraint(equalTo:host.leadingAnchor,constant:inset),content.trailingAnchor.constraint(equalTo:host.trailingAnchor,constant:-inset),content.topAnchor.constraint(equalTo:host.topAnchor,constant:inset),content.bottomAnchor.constraint(equalTo:host.bottomAnchor,constant:-inset)])
    }
    func show(_ window:NSWindow) {window.makeKeyAndOrderFront(nil);NSApp.activate(ignoringOtherApps:true)}
    func section(_ title:String, _ rows:[NSView])->NSView {
        let titleView = label(title,size:11,bold:true);titleView.textColor = .secondaryLabelColor
        let group = NSBox();group.boxType = .custom;group.borderWidth = 0;group.cornerRadius = 10;group.fillColor = .quaternaryLabelColor
        group.translatesAutoresizingMaskIntoConstraints = false
        permissionGroups.append(group)
        let body = stack(rows);body.translatesAutoresizingMaskIntoConstraints = false;group.contentView?.addSubview(body)
        if let container = group.contentView {NSLayoutConstraint.activate([body.leadingAnchor.constraint(equalTo:container.leadingAnchor,constant:12),body.trailingAnchor.constraint(equalTo:container.trailingAnchor,constant:-12),body.topAnchor.constraint(equalTo:container.topAnchor,constant:12),body.bottomAnchor.constraint(equalTo:container.bottomAnchor,constant:-12)])}
        for row in rows {row.widthAnchor.constraint(equalTo:body.widthAnchor).isActive = true}
        let result = stack([titleView,group],spacing:8)
        group.widthAnchor.constraint(equalTo:result.widthAnchor).isActive = true
        return result
    }
    func check(_ title:String,key:String,enabled:Bool = true)->NSButton {
        let view = NSButton(checkboxWithTitle:title,target:self,action:#selector(changeCheck(_:)))
        view.identifier = NSUserInterfaceItemIdentifier(key);view.state = (settings[key] as? Bool ?? false) ? .on : .off;view.isEnabled = enabled
        return view
    }
    func handle(_ command:String,payload:String) {
        guard let data = payload.data(using:.utf8),let value = try? JSONSerialization.jsonObject(with:data) as? [String:Any] else{return}
        if command == "permissions" { settings = value;showPermissions() }
        if command == "applications" { settings = value;showApplications() }
        if command == "welcome" {showWelcome(value)}
        if command == "approval" {
            let alert = NSAlert();alert.messageText = "Approve Pico action?"
            let tool = value["tool"] as? String ?? "Action"
            let folder = value["folder"] as? String ?? ""
            let args = value["arguments"] as? [String:Any] ?? [:]
            let raw = (try? JSONSerialization.data(withJSONObject:args,options:[.prettyPrinted,.sortedKeys])) ?? Data()
            alert.informativeText = "\(tool)\nFolder: \(folder)\n\nCommands run as your user account. Review the exact action below."
            let scroll = NSScrollView(frame:NSRect(x:0,y:0,width:480,height:220));scroll.hasVerticalScroller = true
            let text = NSTextView(frame:scroll.bounds);text.isEditable = false;text.font = .monospacedSystemFont(ofSize:12,weight:.regular);text.string = String(data:raw,encoding:.utf8) ?? "";scroll.documentView = text;alert.accessoryView = scroll
            alert.addButton(withTitle:"Cancel");alert.addButton(withTitle:"Approve once")
            let allowed = alert.runModal() == .alertSecondButtonReturn
            emit(["action":"task_approval","id":value["id"] as? String ?? "","allowed":allowed])
        }
        if command == "notice" {let alert = NSAlert();alert.messageText = value["message"] as? String ?? "Pico";alert.runModal()}
    }
    func showPermissions() {
        permissionGroups = []
        let window = permissions ?? panel("Pico permissions",width:580,height:720);permissions = window
        let scroll = NSScrollView();scroll.hasVerticalScroller = true;scroll.drawsBackground = false;scroll.contentView = TopAlignedClipView();scroll.autohidesScrollers = true
        let body = stack([]);preferencesStack = body;body.edgeInsets = NSEdgeInsets(top:0,left:0,bottom:12,right:0)
        scroll.documentView = body;body.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([body.leadingAnchor.constraint(equalTo:scroll.contentView.leadingAnchor),body.trailingAnchor.constraint(equalTo:scroll.contentView.trailingAnchor),body.topAnchor.constraint(equalTo:scroll.contentView.topAnchor),body.widthAnchor.constraint(equalTo:scroll.contentView.widthAnchor)])
        let title = label("Let Pico hold your place",size:23,bold:true)
        let subtitle = label("Changes save as you go.");subtitle.textColor = .secondaryLabelColor
        let interval = NSPopUpButton();interval.addItems(withTitles:["1 minute","2 minutes","5 minutes"])
        interval.selectItem(at:[1,2,5].firstIndex(of:settings["idle_minutes"] as? Int ?? 2) ?? 1);interval.target = self;interval.action = #selector(changeInterval(_:))
        let idle = stack([check("Notice when I step away",key:"notice_idle"),interval],vertical:false)
        let screen = CGPreflightScreenCaptureAccess()
        let status = label(screen ? "Screen access allowed" : "Screen access not granted",size:12);status.textColor = .secondaryLabelColor
        let access = stack([status,button("Open System Settings",#selector(openScreenSettings))],vertical:false)
        let hold = section("Hold my place",[idle,check("Snapshot the window I’m working in",key:"snapshots"),access])
        let configured = settings["model_configured"] as? Bool ?? false
        let modelHint = label(configured ? "Uses your configured model provider." : "Head Start is not connected yet.",size:12);modelHint.textColor = .secondaryLabelColor
        let head = section("Head Start",[check("Prepare my next step while I’m away",key:"prepare",enabled:configured),check("Allow the snapshot to be sent to my model provider",key:"share_snapshot",enabled:configured),check("Reopen the app when I continue",key:"reopen"),modelHint])
        var exclusions:[NSView] = [label("Choose apps that Pico should never snapshot.",size:12)]
        for item in settings["excluded_apps"] as? [[String:String]] ?? [] {
            let name = label(item["name"] ?? "App")
            let remove = button("Remove",#selector(removeApp(_:)));remove.identifier = NSUserInterfaceItemIdentifier(item["bundle"] ?? "")
            exclusions.append(stack([name,remove],vertical:false))
        }
        exclusions.append(button("Add an app…",#selector(addApp)))
        let apps = section("Never snapshot these apps",exclusions)
        let retention = NSPopUpButton();retention.addItems(withTitles:["1 day","7 days","30 days"]);retention.selectItem(at:[1,7,30].firstIndex(of:settings["retention_days"] as? Int ?? 7) ?? 1);retention.target = self;retention.action = #selector(changeRetention(_:))
        let files = section("Snapshots folder",[label("Pictures / PICO Places",size:12),stack([label("Keep finished snapshots for",size:12),retention],vertical:false),stack([button("Open folder",#selector(openFolder)),button("Clear snapshots…",#selector(clearSnapshots))],vertical:false)])
        for view in [title,subtitle,appAccessSection(),folderAccessSection(),hold,head,apps,files] {body.addArrangedSubview(view);view.widthAnchor.constraint(equalTo:body.widthAnchor).isActive = true}
        let paired = settings["paired"] as? Bool ?? false
        var connection:[NSView] = [label(paired ? "Paired with your account" : "No phone paired",size:13)]
        if paired {connection.append(button("Unpair…",#selector(unpair)))}
        let connected = section("Phone",connection);body.addArrangedSubview(connected);connected.widthAnchor.constraint(equalTo:body.widthAnchor).isActive = true
        let safety = label("Pico asks before any send, submit, delete or purchase.",size:12);safety.textColor = .secondaryLabelColor;body.addArrangedSubview(safety)
        let doneButton = button("Done",#selector(done));doneButton.keyEquivalent = "\r"
        let spacer = NSView();spacer.setContentHuggingPriority(.defaultLow,for:.horizontal)
        let footer = stack([button("Pause for 1 hour",#selector(pause)),spacer,doneButton],vertical:false)
        let outer = stack([scroll,footer]);outer.alignment = .leading
        scroll.widthAnchor.constraint(equalTo:outer.widthAnchor).isActive = true
        footer.widthAnchor.constraint(equalTo:outer.widthAnchor).isActive = true
        mount(outer,in:window);show(window)
        if CommandLine.arguments.contains("--verify-layout") {DispatchQueue.main.async {window.contentView?.layoutSubtreeIfNeeded();self.emit(["permission_widths":self.permissionGroups.map{$0.frame.width}])}}
    }
    func save(){emit(["action":"preferences","values":settings])}
    @objc func changeCheck(_ sender:NSButton){guard let key = sender.identifier?.rawValue else{return};settings[key] = sender.state == .on;save()}
    @objc func changeInterval(_ sender:NSPopUpButton){settings["idle_minutes"] = [1,2,5][sender.indexOfSelectedItem];save()}
    @objc func changeRetention(_ sender:NSPopUpButton){settings["retention_days"] = [1,7,30][sender.indexOfSelectedItem];save()}
    @objc func addApp(){
        let picker = NSOpenPanel();picker.title = "Never snapshot this app";picker.allowedContentTypes = [.applicationBundle];picker.directoryURL = URL(fileURLWithPath:"/Applications");picker.canChooseDirectories = false;picker.allowsMultipleSelection = false
        guard picker.runModal() == .OK,let url = picker.url,let bundle = Bundle(url:url)?.bundleIdentifier else{return}
        var apps = settings["excluded_apps"] as? [[String:String]] ?? []
        guard !apps.contains(where:{$0["bundle"] == bundle}) else{return}
        apps.append(["name":url.deletingPathExtension().lastPathComponent,"bundle":bundle]);settings["excluded_apps"] = apps;save();showPermissions()
    }
    @objc func removeApp(_ sender:NSButton){let id = sender.identifier?.rawValue;settings["excluded_apps"] = (settings["excluded_apps"] as? [[String:String]] ?? []).filter{$0["bundle"] != id};save();showPermissions()}
    @objc func openScreenSettings(){if let url = URL(string:"x-apple.systempreferences:com.apple.preference.security?Privacy_ScreenCapture"){NSWorkspace.shared.open(url)}}
    @objc func openFolder(){let folder = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Pictures/PICO Places");try? FileManager.default.createDirectory(at:folder,withIntermediateDirectories:true);NSWorkspace.shared.open(folder)}
    @objc func clearSnapshots(){let alert = NSAlert();alert.messageText = "Clear Pico snapshots?";alert.informativeText = "This removes snapshots saved by Pico. Your sentences stay saved.";alert.addButton(withTitle:"Cancel");alert.addButton(withTitle:"Clear snapshots");if alert.runModal() == .alertSecondButtonReturn{emit(["action":"clear_snapshots"])}}
    @objc func unpair(){let alert = NSAlert();alert.messageText = "Unpair this computer?";alert.addButton(withTitle:"Keep connected");alert.addButton(withTitle:"Unpair");if alert.runModal() == .alertSecondButtonReturn{emit(["action":"unpair"]);permissions?.close()}}
    @objc func pause(){emit(["action":"pause"]);permissions?.close()}
    @objc func done(){permissions?.close()}
    func showWelcome(_ value:[String:Any]) {
        currentID = value["id"] as? String ?? "";currentText = value["head_start"] as? String ?? value["sentence"] as? String ?? ""
        let window = welcome ?? panel("Pico",width:420,height:240);welcome = window
        let title = label("Welcome back",size:23,bold:true)
        let sentence = label(value["sentence"] as? String ?? "",size:15)
        let head = label(value["head_start"] as? String ?? "Your place is ready.",size:13);head.textColor = .secondaryLabelColor
        let text = stack([sentence,head],spacing:12)
        let scroll = NSScrollView();scroll.drawsBackground = false;scroll.contentView = TopAlignedClipView();scroll.autohidesScrollers = true;scroll.hasVerticalScroller = true;scroll.documentView = text
        text.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([text.leadingAnchor.constraint(equalTo:scroll.contentView.leadingAnchor),text.trailingAnchor.constraint(equalTo:scroll.contentView.trailingAnchor),text.topAnchor.constraint(equalTo:scroll.contentView.topAnchor),text.widthAnchor.constraint(equalTo:scroll.contentView.widthAnchor)])
        let resume = button("Continue",#selector(resume));resume.keyEquivalent = "\r"
        let park = button("Park it",#selector(park))
        let actions = stack([park,resume],vertical:false);actions.distribution = .fillEqually
        let content = stack([title,scroll,actions],spacing:16)
        scroll.widthAnchor.constraint(equalTo:content.widthAnchor).isActive = true
        actions.widthAnchor.constraint(equalTo:content.widthAnchor).isActive = true
        mount(content,in:window);show(window)
    }
    @objc func resume(){NSPasteboard.general.clearContents();NSPasteboard.general.setString(currentText,forType:.string);emit(["action":"place_action","id":currentID,"choice":"continue"]);welcome?.close()}
    @objc func park(){emit(["action":"place_action","id":currentID,"choice":"park"]);welcome?.close()}
}
