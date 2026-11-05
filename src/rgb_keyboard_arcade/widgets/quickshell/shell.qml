import QtQuick
import Quickshell
import Quickshell.Io
ShellRoot {
    id: root
    property var state: ({mode:"default",phase:"idle",score:0,pixels:[]})
    property var layout: []
    function send(message) { if (engine.connected) {engine.write(JSON.stringify(message)+"\n");engine.flush();} }
    Socket {
        id:engine
        path:Quickshell.env("RGB_KEYBOARD_ARCADE_SOCKET") || (Quickshell.env("XDG_RUNTIME_DIR")+"/rgb-keyboard-arcade.sock")
        connected:true
        onConnectedChanged:if (connected) root.send({op:"watch"})
        parser:SplitParser { onRead:data=>{try {let s=JSON.parse(data);root.state=s;if(s.layout)root.layout=s.layout;}catch(e){console.warn("Invalid arcade state");}} }
    }
    Timer {interval:1000;running:!engine.connected;repeat:true;onTriggered:engine.connected=true}
    PanelWindow {
        id:window
        anchors {top:true;right:true}
        margins {top:16;right:16}
        implicitWidth:414;implicitHeight:panel.implicitHeight;color:"transparent"
        KeyboardPanel {
            id:panel
            anchors.fill:parent;gameState:root.state;layout:root.layout;connected:engine.connected
            onChoose:mode=>root.send({op:"mode",mode:mode})
            onConfigure:(gameMode,difficulty)=>root.send({op:"settings",game_mode:gameMode,difficulty:difficulty})
            onSelectGame:game=>root.send({op:"select_game",game:game})
            onRestart:root.send({op:"restart"})
            onPress:(row,column)=>root.send({op:"key_down",row:row,column:column})
            onRelease:(row,column)=>root.send({op:"key_up",row:row,column:column})
            onDismiss:Qt.quit()
        }
    }
}
