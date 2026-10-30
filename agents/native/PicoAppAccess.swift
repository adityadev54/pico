import AppKit
import UniformTypeIdentifiers

extension CompanionPanels {
    func appAccessSection() -> NSView {
        var rows: [NSView] = [label("Only apps you choose here can be opened from your phone.", size:12)]
        for app in settings["allowed_apps"] as? [[String:String]] ?? [] {
            let open = button("Open", #selector(openAllowed(_:)))
            let remove = button("Remove", #selector(removeAllowed(_:)))
            open.identifier = NSUserInterfaceItemIdentifier(app["id"] ?? "")
            remove.identifier = open.identifier
            rows.append(stack([label(app["name"] ?? "App"), open, remove], vertical:false))
        }
        rows.append(button("Choose an app…", #selector(addAllowed)))
        return section("Apps Pico can open", rows)
    }
    func showApplications() {
        let window = applications ?? panel("Pico apps", width:540, height:440)
        applications = window
        let scroll = NSScrollView(); scroll.hasVerticalScroller = true; scroll.autohidesScrollers = true; scroll.drawsBackground = false
        scroll.contentView = TopAlignedClipView()
        let group = appAccessSection(); scroll.documentView = group
        group.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([group.leadingAnchor.constraint(equalTo:scroll.contentView.leadingAnchor), group.topAnchor.constraint(equalTo:scroll.contentView.topAnchor), group.widthAnchor.constraint(equalTo:scroll.contentView.widthAnchor)])
        let hint = label("App opening and snapshot exclusions are separate permissions.", size:12); hint.textColor = .secondaryLabelColor
        let permissions = button("Permissions…", #selector(appPermissions))
        let content = stack([scroll, hint, permissions]); scroll.widthAnchor.constraint(equalTo:content.widthAnchor).isActive = true
        mount(content, in:window); show(window)
    }
    @objc func addAllowed() {
        var apps = settings["allowed_apps"] as? [[String:String]] ?? []
        if apps.count >= 20 { let alert = NSAlert(); alert.messageText = "Choose up to 20 apps."; alert.runModal(); return }
        let picker = NSOpenPanel(); picker.title = "Allow Pico to open this app"; picker.allowedContentTypes = [.applicationBundle]
        picker.directoryURL = URL(fileURLWithPath:"/Applications"); picker.allowsMultipleSelection = false; picker.canChooseDirectories = false
        guard picker.runModal() == .OK, let url = picker.url, let bundle = Bundle(url:url)?.bundleIdentifier else { return }
        if apps.contains(where: { $0["bundle"] == bundle }) { return }
        apps.append(["id":UUID().uuidString.lowercased(), "name":String(url.deletingPathExtension().lastPathComponent.prefix(40)), "bundle":bundle])
        settings["allowed_apps"] = apps; save(); showApplications()
        if permissions?.isVisible == true { showPermissions() }
    }
    @objc func removeAllowed(_ sender:NSButton) {
        settings["allowed_apps"] = (settings["allowed_apps"] as? [[String:String]] ?? []).filter { $0["id"] != sender.identifier?.rawValue }
        save(); showApplications()
        if permissions?.isVisible == true { showPermissions() }
    }
    @objc func openAllowed(_ sender:NSButton) { if let id = sender.identifier?.rawValue { emit(["action":"open_app", "id":id]) } }
    @objc func appPermissions() { emit(["action":"permissions"]) }
}

extension CompanionPanels {
    func folderAccessSection() -> NSView {
        var rows:[NSView] = [label("Choose read-only or write access. Each write or command also needs your approval here.",size:12)]
        for grant in settings["grants"] as? [[String:String]] ?? [] {
            let path = grant["path"] ?? ""
            let remove = button("Remove",#selector(removeReadFolder(_:)));remove.identifier = NSUserInterfaceItemIdentifier(path)
            rows.append(stack([label(URL(fileURLWithPath:path).lastPathComponent + " · " + (grant["access"] ?? "read")),remove],vertical:false))
        }
        rows.append(stack([button("Read-only folder…",#selector(addReadFolder)),button("Write workspace…",#selector(addWriteFolder))],vertical:false))
        return section("Approved folders",rows)
    }
    @objc func addReadFolder() { chooseFolder(access:"read") }
    @objc func addWriteFolder() { chooseFolder(access:"write") }
    func chooseFolder(access:String) {
        var grants = settings["grants"] as? [[String:String]] ?? []
        guard grants.count < 20 else {return}
        let picker = NSOpenPanel();picker.title = access == "write" ? "Allow reviewed writes in this folder" : "Allow Pico to read this folder";picker.canChooseDirectories = true;picker.canChooseFiles = false
        guard picker.runModal() == .OK, let url = picker.url else {return}
        grants.removeAll(where:{$0["path"] == url.path});grants.append(["path":url.path,"access":access])
        settings["grants"] = grants;save();showPermissions()
    }
    @objc func removeReadFolder(_ sender:NSButton) {
        settings["grants"] = (settings["grants"] as? [[String:String]] ?? []).filter{$0["path"] != sender.identifier?.rawValue}
        save();showPermissions()
    }
}
