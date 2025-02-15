#!/usr/bin/env python3

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

headers = ["Cue Number", "Cue Name", "DCA1", "DCA2", "DCA3", "DCA4", "DCA5", "DCA6", "DCA7", "DCA8"]

class LS9MixTableModel(QAbstractTableModel):
    def __init__(self, mix):
        super().__init__()
        self.mix = mix
    
    def rowCount(self, parent):
        return len(self.mix.cues)
    
    def columnCount(self, parent):
        return len(headers)
    
    def data(self, index, role):
        if role == Qt.ItemDataRole.BackgroundRole:
            cue_num = index.row()
            cue = self.mix.cues.get_cue(cue_num)
            column = index.column()
            if column > 1:
                dca = column - 2
                if cue_num < len(self.mix.cues) - 1:
                    if cue.dca[ls9.controlled_dca[dca]] == self.mix.cues.get_cue(cue_num + 1).dca[ls9.controlled_dca[dca]] and cue.dca[ls9.controlled_dca[dca]] != []:
                        if cue.effects[ls9.controlled_dca[dca]] == self.mix.cues.get_cue(cue_num + 1).effects[ls9.controlled_dca[dca]]:
                            return QColor("#00D000")
                        else:
                            return QColor("#FF7F00")
                    # If one DCA is merged into another DCA in the next CUE, both DCAs colored purple
                    if cue.dca[ls9.controlled_dca[dca]] == self.mix.cues.get_cue(cue_num + 1).dca[ls9.controlled_dca[dca]] and cue.dca[ls9.controlled_dca[dca]] != []:
                        return QColor("#FF00FF")

            if self.mix.current_cue == cue_num:
                return QColor("#0000FF")
            else:
                return QColor("#000000")
        elif role == Qt.ItemDataRole.DisplayRole:
            cue_num = index.row()
            if index.column() == 0:
                if self.mix.current_cue == cue_num:
                    return "> " + str(self.mix.cues.get_cue(cue_num).number)
                else:
                    return self.mix.cues.get_cue(cue_num).number
            elif index.column() == 1:
                return self.mix.cues.get_cue(cue_num).name
            else:
                dca = index.column() - 2
                if len(self.mix.cues.get_cue(cue_num).dca[ls9.controlled_dca[dca]]) == 0:
                    return ""
                elif self.mix.cues.get_cue(cue_num).dca_name[ls9.controlled_dca[dca]] != "":
                    return self.mix.cues.get_cue(cue_num).dca_name[ls9.controlled_dca[dca]]
                elif len(self.mix.cues.get_cue(cue_num).dca[ls9.controlled_dca[dca]]) == 1:
                    return self.mix.cues.get_cue(cue_num).dca[ls9.controlled_dca[dca]][0]
                else:
                    return "Group"
        return QVariant()
    
    def headerData(self, section, orientation, role):
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return QVariant()
        return headers[section]

class LS9MixTableView(QTableView):
    def __init__(self, mix):
        super().__init__()
        self.model = LS9MixTableModel(mix)
        self.mode = 1
        self.mix = mix
        self.setModel(self.model)
        
        # Add a row of controls at the bottom
        self.control_layout = QHBoxLayout()
        self.control_layout.addWidget(QPushButton("Go"))
        self.control_layout.addWidget(QPushButton("Back"))

        self.control_widget = QWidget()
        self.control_widget.setLayout(self.control_layout)
        
        self.layout = QVBoxLayout()
        self.layout.addWidget(self.control_widget)

        self.doubleClicked.connect(self.handle_double_click)
        mix.register_event_callback(self.ls9_message_callback)
    
    def ls9_message_callback(self, cue_num):
        self.update()

    
    def handle_double_click(self, index):
        if self.mode == 0:
            cue_num = index.row()
            self.model.mix.go_cue(cue_num)
        else:
            # Edit Mode
            cue_num = index.row()
            column = index.column()
            if cue_num == 0:
                return
            if column == 0:
                # Replace the cell with a textbox to edit the cue number
                edit = QLineEdit()
                edit.setText(str(self.model.mix.cues.get_cue(cue_num).number))

                def edit_finish():
                    try:
                        float(edit.text())
                    except ValueError:
                        self.setIndexWidget(index, None)
                        return
                    
                    self.mix.cues.change_number(cue_num, float(edit.text()))
                    self.setIndexWidget(index, None)
                    self.update()

                # On clicking away, save the new cue number
                edit.editingFinished.connect(edit_finish)
                self.setIndexWidget(index, edit)
            elif column == 1:
                edit = QLineEdit()
                edit.setText(self.model.mix.cues.get_cue(cue_num).name)

                def edit_finish():
                    self.mix.cues.change_name(cue_num, edit.text())
                    self.setIndexWidget(index, None)
                    self.update()
                
                edit.editingFinished.connect(edit_finish)
                self.setIndexWidget(index, edit)



class MidiSetupWidget(QWidget):
    def __init__(self, server):
        super().__init__()
        self.server = server
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        midi_input = QComboBox()
        midi_output = QComboBox()
        self.layout.addWidget(QLabel("MIDI Input"))
        self.layout.addWidget(midi_input)
        self.layout.addWidget(QLabel("MIDI Output"))
        self.layout.addWidget(midi_output)
        midi_input.addItems(self.server.get_midi_in_ports())
        midi_output.addItems(self.server.get_midi_out_ports())
        midi_input.currentIndexChanged.connect(self.midi_input_changed)
        midi_output.currentIndexChanged.connect(self.midi_output_changed)
        
        # Add OK button
        self.ok_button = QPushButton("OK")
        self.layout.addWidget(self.ok_button)
        self.ok_button.clicked.connect(self.start)
    
    def midi_input_changed(self, index):
        self.server.set_midi_in_port(index)
    
    def midi_output_changed(self, index):
        self.server.set_midi_out_port(index)
    
    def mode_button_clicked(self):
        if self.view.mode == 0:
            self.view.mode = 1
            self.mode_button.setText("Edit Mode")
        else:
            self.view.mode = 0
            self.mode_button.setText("Show Mode")

    def start(self):
        self.server.start()
        for idx in range(self.layout.count()):
            self.layout.itemAt(idx).widget().hide()
            self.layout.itemAt(idx).widget().deleteLater()

        # Save Button
        self.save_button = QPushButton("Save")
        def save():
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Mix", "", "LS9 Mix Files (*.ls9mix)",)
            if file_name == "":
                return
            self.server.save(file_name)
        self.save_button.clicked.connect(save)

        # Load Button
        self.load_button = QPushButton("Load")
        def load():
            file_name, _ = QFileDialog.getOpenFileName(self, "Open Mix", "", "LS9 Mix Files (*.ls9mix)",)
            if file_name == "":
                return
            self.server.load(file_name)
            self.view.model.beginResetModel()
            self.view.model.endResetModel()
            self.view.update()
        self.load_button.clicked.connect(load)

        
        # Show Mode Button
        self.mode_button = QPushButton("Edit Mode")
        self.mode_button.clicked.connect(self.mode_button_clicked)

        # Add CUE button
        self.cue_button = QPushButton("Add CUE")
        def add_cue():
            self.view.model.beginInsertRows(QModelIndex(), len(self.view.model.mix.cues), len(self.view.model.mix.cues))
            if self.view.selectedIndexes() == []:
                self.mix.cues.add_cue()
            else:
                self.mix.cues.add_cue_at(self.view.selectedIndexes()[0].row())
                self.view.selectRow(self.view.selectedIndexes()[0].row() + 1)
            self.view.model.endInsertRows()
            self.view.update()
        self.cue_button.clicked.connect(add_cue)

        # Duplicate CUE button
        self.duplicate_button = QPushButton("Duplicate CUE")
        def duplicate_cue():
            self.view.model.beginInsertRows(QModelIndex(), len(self.view.model.mix.cues), len(self.view.model.mix.cues))
            if self.view.selectedIndexes() == []:
                self.mix.cues.duplicate_cue(len(self.view.model.mix.cues) - 1)
            else:
                self.mix.cues.duplicate_cue(self.view.selectedIndexes()[0].row())
                self.view.selectRow(self.view.selectedIndexes()[0].row() + 1)
            self.view.model.endInsertRows()
            self.view.update()
        self.duplicate_button.clicked.connect(duplicate_cue)

        # Delete CUE button
        self.delete_button = QPushButton("Delete CUE")
        def delete_cue():
            if len(self.view.selectedIndexes()) == 0:
                return
            selected_row = self.view.selectedIndexes()[0].row()
            self.mix.cues.remove_cue(selected_row)
            self.view.model.beginRemoveRows(QModelIndex(), self.view.selectedIndexes()[0].row(), self.view.selectedIndexes()[0].row())
            self.view.model.endRemoveRows()
            self.view.update()
            self.view.selectRow(selected_row)
        self.delete_button.clicked.connect(delete_cue)

        self.control_layout = QHBoxLayout()
        self.control_layout.addWidget(self.save_button)
        self.control_layout.addWidget(self.load_button)
        # A Vertical Spacer
        self.control_layout.addStretch()
        self.control_layout.addWidget(self.mode_button)
        self.control_layout.addStretch()
        self.control_layout.addWidget(self.cue_button)
        self.control_layout.addWidget(self.duplicate_button)
        self.control_layout.addWidget(self.delete_button)
        

        self.control_widget = QWidget()
        self.control_widget.setLayout(self.control_layout)
        self.layout.addWidget(self.control_widget)

        self.mix = self.server.mix
        self.view = LS9MixTableView(self.mix)
        self.layout.addWidget(self.view)

        self.setStyleSheet("background-color: #000000; color: #FFFFFF;")
        self.showMaximized()


if __name__ == '__main__':

    import sys
    import ls9

    app = QApplication([])

    server = ls9.LS9_mix_server()

    midi_setup = MidiSetupWidget(server)
    midi_setup.show()
    
    sys.exit(app.exec())