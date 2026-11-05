pragma ComponentBehavior: Bound
import QtQuick
import QtQuick.Controls
import Quickshell
Rectangle {
    id: panel
    required property var gameState
    required property var layout
    required property bool connected
    signal choose(string mode)
    signal restart()
    signal configure(string gameMode, int difficulty)
    signal press(int row, int column)
    signal release(int row, int column)
    signal selectGame(string game)
    signal dismiss()
    color: "#211b17"
    radius: 15
    border.color: "#695042"
    border.width: 1
    implicitWidth: 414
    implicitHeight: (gameState.mode === "passive" ? 566 : 436) + (gameState.game_id === "mines" ? 18 : gameState.game_id === "pong" ? 30 : 0)
    function cellLabel(key) {
        for (let p of (gameState.cell_labels || [])) if (p[0] === key.row && p[1] === key.column) return String(p[2]);
        return "";
    }
    function playable(key) {
        if (gameState.mode === "default") return true;
        return (gameState.playfield || []).some(p => p[0] === key.row && p[1] === key.column);
    }
    function pixelColor(key) {
        if (gameState.mode === "default") return "#a46a48";
        let list = gameState.pixels || [];
        for (let p of list) if (p[0] === key.row && p[1] === key.column)
            return Qt.rgba(p[2]/255, p[3]/255, p[4]/255, 1);
        return playable(key) ? "#33271f" : "#171310";
    }
    Text {
        x: 22; y: 20
        text: "Keyboard"
        color: "#f3ddc3"
        font.family: "Noto Sans"; font.pixelSize: 21; font.weight: Font.DemiBold
    }
    BarButton { x: parent.width - 52; y: 17; label: "×"; hint: "Close"; onClicked: panel.dismiss() }
    Text {
        x: 22; y: 53
        text: gameState.game_id === "mines" && gameState.mode === "classic" ? "Release: reveal · hold 0.45s: flag · Esc: preview" : gameState.game_id === "pong" && gameState.mode === "classic" ? "P1: R Shift / Right · P2: L Shift / L Ctrl" : gameState.mode === "calibration" ? "Tap top to bottom. Pause 2 seconds between columns." : gameState.mode === "classic" ? "Active · Esc returns to passive" : gameState.mode === "passive" ? "Super+Esc: game · `: mode · Tab: difficulty" : "Choose Snake to begin."
        color: "#bca18b"; font.family: "Noto Sans"; font.pixelSize: 12
    }
    Rectangle {
        x: 22; y: 84; width: parent.width-44; height: 146
        color: gameState.mode === "classic" ? "#121824" : "#1b140f"; radius: 9
        Item {
            x: 10; y: 10; width: parent.width-20; height: parent.height-20
            Repeater {
                model: panel.layout
                Rectangle {
                    required property var modelData
                    x: modelData.physical.x / 15 * parent.width + 1
                    y: modelData.physical.y / 6 * parent.height + 1
                    width: modelData.physical.width / 15 * parent.width - 3
                    height: modelData.physical.height / 6 * parent.height - 3
                    radius: 3
                    color: panel.pixelColor(modelData)
                    border.width: 1; border.color: panel.playable(modelData) ? (panel.gameState.mode === "classic" ? "#31445b" : "#654632") : "#2b221c"
                    Behavior on color { ColorAnimation { duration: panel.gameState.mode === "default" ? 90 : 0 } }
                    Text { anchors.centerIn: parent; text: panel.cellLabel(parent.modelData); color:"#fff8ed"; font.family:"Noto Sans"; font.pixelSize:10; font.bold:true }
                    MouseArea {
                        anchors.fill: parent
                        enabled: panel.connected && ["passive", "classic"].includes(panel.gameState.mode)
                            && (["running", "powering", "staging"].includes(panel.gameState.phase) || modelData.label === "Esc" || (panel.gameState.phase === "dying" && (panel.gameState.game_id === "mines" || ["Up", "Right", "Down", "Left"].includes(modelData.label))))
                            && (panel.playable(modelData) || (panel.gameState.control_cells || []).some(c => c[0] === modelData.row && c[1] === modelData.column) || (panel.gameState.game_id === "pong" && ["R Shift", "L Shift", "L Ctrl"].includes(modelData.label)) || ["Esc", "Up", "Right", "Down", "Left"].includes(modelData.label) || (panel.gameState.selectors_enabled && ["`", "Tab"].includes(modelData.label)))
                        cursorShape: enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
                        onPressed: panel.press(modelData.row, modelData.column)
                        onReleased: panel.release(modelData.row, modelData.column)
                        onCanceled: panel.release(modelData.row, modelData.column)
                    }
                }
            }
        }
    }
    Text {
        x: 24; y: 241; width: parent.width-110; elide: Text.ElideRight
        text: panel.gameState.status_text ? panel.gameState.status_text : !panel.connected ? "Keyboard service reconnecting…" : panel.gameState.error ? panel.gameState.error : panel.gameState.mode === "calibration" ? (panel.gameState.phase === "complete" ? "All game keys saved · typing restored" : panel.gameState.score + "/" + (panel.gameState.playfield || []).length + " recorded · Esc stops") : panel.gameState.mode === "default" ? "Spectrum lighting · no game running" : panel.gameState.phase === "handoff" ? "Release keys to start playing…" : panel.gameState.phase === "revealing" ? "Active round starting…" : panel.gameState.phase === "starting" ? "Starting…" : panel.gameState.phase === "staging" ? "Stage " + (panel.gameState.stage || 1) + " · " + (panel.gameState.stage_seconds || 0).toFixed(1) + "s · get ready…" : panel.gameState.phase === "powering" ? "Rainbow ripple…" : panel.gameState.phase === "ready" ? "Arrows start · Esc exits" : panel.gameState.phase === "dying" && panel.gameState.pending_active && !String(panel.gameState.death_stage).startsWith("entry_") ? "Next round queued…" : panel.gameState.phase === "dying" && panel.gameState.death_reason === "timeout" ? "Apple expired…" : panel.gameState.phase === "dying" && panel.gameState.death_reason === "bomb" ? "Bomb hit!" : panel.gameState.phase === "dying" ? ({wave:"Chain reaction…",charge:"Critical!",burst:"Burst!",entry_ignite:"Breaking into sparks…",entry_burst:"Scattering sparks…",entry_pull:"Pulling into place…",entry_settle:"Active snake ready…",prism_wave:"Rainbow overload…",prism_charge:"Prism charged!",prism_burst:"Spectrum burst!",blackout:"Lights out…"}[panel.gameState.death_stage] || "Game over…") : panel.gameState.mode === "passive" ? ((panel.gameState.game_mode_name || "Rainbow") + " preview · " + (panel.gameState.difficulty_name || "Easy") + (panel.gameState.game_mode === "timer" ? " · " + (panel.gameState.apple_seconds || 0).toFixed(1) + "s" : " · always rainbow")) : panel.gameState.game_mode === "timer" ? "Timer · " + (panel.gameState.apple_seconds || 0).toFixed(1) + "s · Score " + panel.gameState.score : panel.gameState.boost_seconds > 0 ? "Rainbow → Stage " + (panel.gameState.stage || 1) + " · " + panel.gameState.boost_seconds.toFixed(1) + "s · bombs lethal · no food · Score " + panel.gameState.score : panel.gameState.shield_seconds > 0 ? "Spawn shield · " + panel.gameState.shield_seconds.toFixed(1) + "s · portals" : "Stage " + (panel.gameState.stage || 1) + " · " + (panel.gameState.stage_name || "Ember") + " · Score " + panel.gameState.score + "   ·   " + panel.gameState.apples + " apples   ·   Length " + panel.gameState.length
        color: panel.gameState.error ? "#f49b77" : "#bca18b"
        font.family: "Noto Sans"; font.pixelSize: 11
    }
    BarButton {
        anchors.right: parent.right; anchors.rightMargin: 19; y: 232
        label: panel.gameState.phase === "dying" && panel.gameState.pending_active && !String(panel.gameState.death_stage).startsWith("entry_") ? "Queued" : "Restart"; visible: panel.gameState.mode !== "default" && panel.connected
        enabled: !["dying", "revealing", "starting", "entering", "marquee", "powering", "handoff", "staging"].includes(panel.gameState.phase) || (panel.gameState.mode === "classic" && panel.gameState.phase === "dying" && !panel.gameState.pending_active && !String(panel.gameState.death_stage).startsWith("entry_"))
        opacity: enabled ? 1 : .4
        onClicked: panel.restart()
    }
    Item {
        x:22; y:273; width:parent.width-44; height:31
        visible:panel.gameState.mode === "passive"
        Text { x:0;y:8;text:"Game";color:"#c5a58e";font.family:"Noto Sans";font.pixelSize:12 }
        Row {
            x:80;spacing:5
            Repeater {
                model:panel.gameState.games || []
                Rectangle {
                    required property var modelData
                    width:90;height:31;radius:7;color:panel.gameState.game_id === modelData.id ? "#493126" : "#2b221c"
                    border.color:panel.gameState.game_id === modelData.id ? modelData.color : "#594337"
                    Text { anchors.centerIn:parent;text:parent.modelData.label;color:"#f3ddc3";font.family:"Noto Sans";font.pixelSize:11 }
                    MouseArea { anchors.fill:parent;enabled:panel.connected;cursorShape:Qt.PointingHandCursor;onClicked: { if (panel.gameState.game_id !== parent.modelData.id) panel.selectGame(parent.modelData.id); } }
                }
            }
        }
    }
    Item {
        x: 22; y: 313; width: parent.width-44; height: 78
        visible: panel.gameState.mode === "passive"
        enabled: panel.connected && panel.gameState.selectors_enabled === true
        opacity: enabled ? 1 : .45
        Text { x:0; y:8; text:"Mode  `"; color:"#c5a58e"; font.family:"Noto Sans"; font.pixelSize:12 }
        Row {
            x:80; y:0; spacing:6
            Repeater {
                model: panel.gameState.game_modes || []
                Rectangle {
                    required property var modelData
                    width:137; height:31; radius:7
                    color:panel.gameState.game_mode === modelData.id ? "#493126" : "#2b221c"
                    border.color:panel.gameState.game_mode === modelData.id ? "#c58d65" : "#594337"
                    Text { anchors.centerIn:parent; text:parent.modelData.label; color:"#f3ddc3"; font.family:"Noto Sans"; font.pixelSize:12 }
                    MouseArea { anchors.fill:parent; cursorShape:Qt.PointingHandCursor; onClicked:panel.configure(parent.modelData.id,panel.gameState.difficulty) }
                }
            }
        }
        Text { x:0; y:49; text:"Level  Tab"; color:"#c5a58e"; font.family:"Noto Sans"; font.pixelSize:12 }
        Row {
            x:80; y:40; spacing:5
            Repeater {
                model: panel.gameState.difficulties || []
                Rectangle {
                    required property var modelData
                    width:66; height:31; radius:7
                    color:panel.gameState.difficulty === modelData.id ? "#3d3027" : "#2b221c"
                    border.color:panel.gameState.difficulty === modelData.id ? modelData.color : "#594337"
                    Rectangle { x:6;y:11;width:8;height:8;radius:4;color:parent.modelData.color }
                    Text { x:18;anchors.verticalCenter:parent.verticalCenter;text:parent.modelData.label;color:"#f3ddc3";font.family:"Noto Sans";font.pixelSize:10 }
                    MouseArea { anchors.fill:parent;cursorShape:Qt.PointingHandCursor;onClicked:panel.configure(panel.gameState.game_mode,parent.modelData.id) }
                }
            }
        }
    }
    Column {
        x: 12; y: panel.gameState.mode === "passive" ? 405 : 275; width: parent.width-24; spacing: 4
        Repeater {
            model: [
                {mode:"default", title:"Default", detail:"Your everyday lighting", symbol:"◌"},
                {mode:"passive", title:"Game mode", detail:"Super+Esc cycles games · live keyboard previews", symbol:"~"}
            ]
            Rectangle {
                id: choice
                required property var modelData
                width: parent.width; height: 59; radius: 9
                property bool selected: panel.gameState.mode === modelData.mode || (modelData.mode === "passive" && panel.gameState.mode === "classic")
                color: selected ? "#493126" : hit.containsMouse ? "#30231c" : "transparent"
                Behavior on color { ColorAnimation { duration: 120 } }
                Text {
                    x: 13; anchors.verticalCenter: parent.verticalCenter
                    text: choice.modelData.symbol; color: "#edaa7f"
                    font.family: "Noto Sans"; font.pixelSize: 26
                }
                Text { x: 49; y: 9; text: choice.modelData.title; color:"#f3ddc3"; font.family:"Noto Sans"; font.pixelSize:14; font.weight:Font.DemiBold }
                Text { x: 49; y: 31; text: choice.modelData.detail; color:"#c5a58e"; font.family:"Noto Sans"; font.pixelSize:11 }
                Text { anchors.right:parent.right; anchors.rightMargin:15; y:12; text:choice.selected ? "•" : ""; color:"#efab7f"; font.pixelSize:20 }
                MouseArea {
                    id: hit; anchors.fill: parent; hoverEnabled:true; cursorShape:Qt.PointingHandCursor
                    enabled: panel.connected
                    onClicked: { if (!choice.selected) panel.choose(choice.modelData.mode); }
                }
            }
        }
    }
    Text {
        x: 24; y: panel.gameState.mode === "passive" ? 541 : 411
        width:parent.width-44;wrapMode:Text.WordWrap
        text: panel.gameState.game_id === "mines" ? "Tap + release: reveal · hold: flag/unflag. First reveal is safe. Number colors match the exact clues shown above." : panel.gameState.game_id === "pong" ? "First to 3. P1: R Shift up / Right down. P2: L Shift up / L Ctrl down. Difficulty sets ball speed." : panel.gameState.mode === "passive" ? (panel.gameState.game_mode === "rainbow" ? "Tap empty keys to place bombs · Esc returns to Default" : "Preview controls above · Esc returns to Default") : panel.gameState.boost_seconds > 0 && panel.gameState.phase === "running" ? "Tap empty keys to place bombs · flashing bombs kill" : panel.gameState.food_paused ? "Food returns after the stage change · Esc backs out" : panel.gameState.game_mode === "timer" ? "Wrap at edges · eat before food fades" : "Red/white bombs kill · board adds food · 5 taps: rainbow"
        color: "#bca18b"; font.family: "Noto Sans"; font.pixelSize: 11
    }
}
