import QtQuick
import QtQuick.Controls
Rectangle {
    id: button
    property string label: ""
    property string hint: ""
    property bool selected: false
    property color accent: "#e98c67"
    property int horizontalPadding: 12
    signal clicked()
    signal rightClicked()
    signal scrolled(real delta)
    implicitWidth: text.implicitWidth + horizontalPadding * 2
    implicitHeight: 32
    radius: 8
    color: selected ? "#4b3329" : mouse.containsMouse ? "#352821" : "transparent"
    Behavior on color { ColorAnimation { duration: 120 } }
    Text {
        id: text
        anchors.centerIn: parent
        text: button.label
        color: button.selected ? button.accent : "#f3ddc3"
        font.family: "Noto Sans"
        font.pixelSize: 12
        font.weight: button.selected ? Font.DemiBold : Font.Medium
    }
    MouseArea {
        id: mouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: event => event.button === Qt.RightButton ? button.rightClicked() : button.clicked()
        onWheel: event => { button.scrolled(event.angleDelta.y); event.accepted = true; }
    }
    ToolTip.visible: mouse.containsMouse && hint !== ""
    ToolTip.text: hint
    ToolTip.delay: 650
}
