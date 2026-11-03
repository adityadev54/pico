import AppKit
import UniformTypeIdentifiers

extension CompanionPanels {
    func mountStudyScroll(_ body:NSView,in window:NSWindow) {
        let scroll = NSScrollView();scroll.hasVerticalScroller = true;scroll.autohidesScrollers = true;scroll.drawsBackground = false;scroll.contentView = TopAlignedClipView();scroll.documentView = body;body.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([body.leadingAnchor.constraint(equalTo:scroll.contentView.leadingAnchor),body.trailingAnchor.constraint(equalTo:scroll.contentView.trailingAnchor),body.topAnchor.constraint(equalTo:scroll.contentView.topAnchor),body.widthAnchor.constraint(equalTo:scroll.contentView.widthAnchor)])
        // Bound the viewport itself: an unconstrained document view can make
        // AppKit recompute a narrow, tall fitting size after the window opens.
        scroll.widthAnchor.constraint(greaterThanOrEqualToConstant:604).isActive = true
        scroll.heightAnchor.constraint(lessThanOrEqualToConstant:384).isActive = true
        mount(scroll,in:window)
    }
    func showTeaching(_ value:[String:Any]) {
        let w = teaching ?? panel("Teach Pico",width:680,height:360);teaching = w
        let busy = value["busy"] as? Bool ?? false
        let recording = value["recording"] as? Bool ?? false
        let rows = value["routines"] as? [[String:Any]] ?? []
        let message = label(value["message"] as? String ?? "",size:12);message.textColor = .secondaryLabelColor
        let title = label(recording ? "Show me the result you want" : "Watch how I do this",size:17,bold:true)
        let hint = label("Choose source files and an example. Only that example file is watched; no screen or keyboard recording.",size:12)
        var views:[NSView] = [title,hint]
        if !message.stringValue.isEmpty {views.append(message)}
        if recording {
            views += [label("Edit and save your example in TextEdit, then finish teaching."),button("Finish teaching…",#selector(finishTeaching)),button("Stop teaching",#selector(cancelTeaching))]
        } else {
            let choose = button("Select files and example…",#selector(chooseTeaching));choose.isEnabled = !busy
            teachName.placeholderString = "Routine name";if teachName.stringValue.isEmpty {teachName.stringValue = "Prepare my result"}
            views += [teachName,choose,label("Taught routines",size:12,bold:true)]
            if rows.isEmpty { views.append(label("No taught routines yet.",size:12)) }
            for row in rows {
                let b = button("Run \(row["name"] as? String ?? "Routine")…",#selector(runTeaching(_:)))
                b.identifier = NSUserInterfaceItemIdentifier(row["id"] as? String ?? "");b.isEnabled = !busy
                b.toolTip = (row["sources"] as? [String] ?? []).joined(separator:"\n")
                let icon = NSImageView();icon.image = NSImage(systemSymbolName:"arrow.triangle.2.circlepath",accessibilityDescription:nil);icon.widthAnchor.constraint(equalToConstant:16).isActive = true
                let spacer = NSView();spacer.setContentHuggingPriority(.defaultLow,for:.horizontal)
                let name = label(row["name"] as? String ?? "Routine",size:13,bold:true)
                b.title = "Run…"
                views.append(stack([icon,name,spacer,b],vertical:false))
                let notes = button("Choose different files…",#selector(changeStudyNotes(_:)));notes.identifier = b.identifier;notes.toolTip = row["root"] as? String;notes.isEnabled = !busy;var actions:[NSView] = [notes]
                if row["has_output"] as? Bool ?? false {let open = button("Open latest result",#selector(openStudyPack(_:)));open.identifier = b.identifier;actions.append(open)}
                let space = NSView();space.setContentHuggingPriority(.defaultLow,for:.horizontal);actions.append(space);views.append(stack(actions,vertical:false))
            }
        }
        let body = stack(views,spacing:8);mountStudyScroll(body,in:w)
        for v in views { v.widthAnchor.constraint(equalTo:body.widthAnchor).isActive = true }
        w.contentMinSize = NSSize(width:640,height:300)
        w.contentMaxSize = NSSize(width:1000,height:420)
        w.styleMask.insert(.resizable)
        w.setContentSize(NSSize(width:680,height:360))
        show(w)
    }
    @objc func changeStudyNotes(_ sender:NSButton) {
        guard let root = sender.toolTip else{return}
        let picker = NSOpenPanel();picker.directoryURL = URL(fileURLWithPath:root);picker.message = "Choose 1–4 files inside this routine’s workspace";picker.allowsMultipleSelection = true
        guard picker.runModal() == .OK else{return}
        let prefix = root + "/"
        guard picker.urls.allSatisfy({$0.path.hasPrefix(prefix)}) else{return}
        emit(["action":"teach","choice":"sources","id":sender.identifier?.rawValue ?? "","sources":picker.urls.map{String($0.path.dropFirst(prefix.count))}])
    }
    @objc func openStudyPack(_ sender:NSButton) {emit(["action":"teach","choice":"open","id":sender.identifier?.rawValue ?? ""])}
    @objc func chooseTeaching() {
        let rootPicker = NSOpenPanel();rootPicker.message = "Choose a folder already granted write access in Pico Permissions";rootPicker.canChooseDirectories = true;rootPicker.canChooseFiles = false
        guard rootPicker.runModal() == .OK,let root = rootPicker.url else{return}
        let picker = NSOpenPanel();picker.message = "Select 1–4 source files (up to 6,000 characters total)";picker.directoryURL = root;picker.allowsMultipleSelection = true;picker.allowedContentTypes = [.plainText,.pdf,.commaSeparatedText,.init(filenameExtension:"md")!,.init(filenameExtension:"docx")!]
        guard picker.runModal() == .OK else{return}
        let prefix = root.path + "/"
        guard picker.urls.count <= 4,picker.urls.allSatisfy({$0.path.hasPrefix(prefix)}) else {let a = NSAlert();a.messageText = "Select up to four files inside this folder.";a.runModal();return}
        let output = NSSavePanel();output.message = "Choose your example result. You will edit this file, then finish teaching.";output.directoryURL = root;output.nameFieldStringValue = "My example.md";output.allowedContentTypes = [.init(filenameExtension:"md")!]
        guard output.runModal() == .OK,let url = output.url,url.path.hasPrefix(prefix) else{return}
        teachRoot = root.path;teachSources = picker.urls.map{String($0.path.dropFirst(prefix.count))};teachOutput = String(url.path.dropFirst(prefix.count))
        emit(["action":"teach","choice":"start","root":teachRoot,"sources":teachSources,"output":teachOutput])
    }
    @objc func finishTeaching() {
        let alert = NSAlert();alert.messageText = "Learn from these selected files?"
        alert.informativeText = "Send only these source files and your saved example to Muse:\n\n\(teachSources.joined(separator:"\n"))\n\(teachOutput)\n\nA paid model request uses your existing account limits. No automatic retries."
        alert.addButton(withTitle:"Keep local");alert.addButton(withTitle:"Send and learn")
        if alert.runModal() == .alertSecondButtonReturn { emit(["action":"teach","choice":"finish","name":teachName.stringValue,"confirmed":true]) }
    }
    @objc func cancelTeaching() {emit(["action":"teach","choice":"cancel"])}
    @objc func runTeaching(_ sender:NSButton) {
        let alert = NSAlert();alert.messageText = "Prepare a new result?";alert.informativeText = "Send the current contents of these source files to Muse:\n\n\(sender.toolTip ?? "")\n\nA new Markdown result is saved beside your example. Existing files are kept. Uses your account limits."
        alert.addButton(withTitle:"Cancel");alert.addButton(withTitle:"Run once")
        if alert.runModal() == .alertSecondButtonReturn {emit(["action":"teach","choice":"run","id":sender.identifier?.rawValue ?? "","confirmed":true])}
    }
    func showPlaces(_ value:[String:Any]) {
        let rows = value["places"] as? [[String:Any]] ?? []
        let w = placesWindow ?? panel("Parked Places",width:460,height:400);placesWindow = w
        var views:[NSView] = [label("Parked Places",size:17,bold:true)]
        if rows.isEmpty {views.append(label("No waiting or parked Places."))}
        for row in rows.prefix(8) {
            let b = button(row["sentence"] as? String ?? "Saved place",#selector(openSavedPlace(_:)));b.identifier = NSUserInterfaceItemIdentifier(row["id"] as? String ?? "");views.append(b)
            views.append(label("\(row["app"] as? String ?? "") · \(row["status"] as? String ?? "")",size:12))
        }
        views.append(NSView());mountStudyScroll(stack(views,spacing:10),in:w);show(w)
    }
    @objc func openSavedPlace(_ sender:NSButton) {emit(["action":"open_place","id":sender.identifier?.rawValue ?? ""])}
}
