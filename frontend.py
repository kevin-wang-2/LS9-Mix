#!/usr/bin/env python3

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *
import qdarktheme

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
                    return self.mix.input_alias[self.mix.cues.get_cue(cue_num).dca[ls9.controlled_dca[dca]][0]]
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

        self.clipboard_mode = 0 # 0: Nothing, 1: Copy Whole Cue, 2: Copy DCA
    
    def keyPressEvent(self, e):
        # ctrl
        if e.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if e.key() == Qt.Key.Key_D:
                self.parent().duplicate_button.click()
            elif e.key() == Qt.Key.Key_C:
                # if no selection do nothing
                if len(self.selectedIndexes()) == 0:
                    return

                # if selected the first or second column, copy the whole cue
                if self.selectedIndexes()[0].column() == 0 or self.selectedIndexes()[0].column() == 1:
                    self.clipboard_mode = 1
                    self.clipboard = self.selectedIndexes()[0].row()
                else:
                    self.clipboard_mode = 2
                    assignment = self.mix.cues.get_cue(self.selectedIndexes()[0].row()).dca[ls9.controlled_dca[self.selectedIndexes()[0].column() - 2]].copy()
                    effects = self.mix.cues.get_cue(self.selectedIndexes()[0].row()).effects[ls9.controlled_dca[self.selectedIndexes()[0].column() - 2]].copy()
                    dca_name = self.mix.cues.get_cue(self.selectedIndexes()[0].row()).dca_name[ls9.controlled_dca[self.selectedIndexes()[0].column() - 2]]

                    self.clipboard = (assignment, effects, dca_name)
            elif e.key() == Qt.Key.Key_V:
                if self.clipboard_mode == 0:
                    return
                if self.clipboard_mode == 1:
                    if self.selectedIndexes() == []:
                        self.mix.cues.copy_cue(self.clipboard)
                    else:
                        self.mix.cues.copy_cue_to(self.clipboard, self.selectedIndexes()[0].row())
                    self.model.beginInsertRows(QModelIndex(), len(self.model.mix.cues), len(self.model.mix.cues))
                    self.model.endInsertRows()
                    self.update()
                else:
                    # If selected on first two columns, do nothing
                    if self.selectedIndexes()[0].column() == 0 or self.selectedIndexes()[0].column() == 1:
                        return
                    # Remove the inputs in this DCA from all the DCAs on the current CUE
                    assingment = self.clipboard[0].copy()
                    effects = self.clipboard[1].copy()
                    dca_name = self.clipboard[2]

                    for input in assingment:
                        for dca in ls9.controlled_dca:
                            if input in self.mix.cues.get_cue(self.selectedIndexes()[0].row()).dca[dca]:
                                self.mix.cues.remove_input_from_dca(self.selectedIndexes()[0].row(), dca, input)
                                if len(self.mix.cues.get_cue(self.selectedIndexes()[0].row()).dca[dca]) == 0:
                                    self.mix.cues.set_effects_of_dca(self.selectedIndexes()[0].row(), dca, [])

                    # Paste on current DCA
                    self.mix.cues.set_input_of_dca(self.selectedIndexes()[0].row(), ls9.controlled_dca[self.selectedIndexes()[0].column() - 2], assingment)
                    self.mix.cues.set_effects_of_dca(self.selectedIndexes()[0].row(), ls9.controlled_dca[self.selectedIndexes()[0].column() - 2], effects)
                    self.mix.cues.change_dca_name(self.selectedIndexes()[0].row(), ls9.controlled_dca[self.selectedIndexes()[0].column() - 2], dca_name)

                    # If it's current cue and console connected, go cue
                    if self.mix.current_cue == self.selectedIndexes()[0].row() and self.mix.connected:
                        self.mix.go_cue(self.selectedIndexes()[0].row())
                    self.update()
                

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
            else:
                dca = column - 2
                dialog = DCAEditDialog(self, cue_num, dca)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    assignment = sorted(dialog.assignment)

                    for i in assignment:
                        for other_assignment in self.mix.cues.get_cue(cue_num).dca:
                            if i in self.mix.cues.get_cue(cue_num).dca[other_assignment] and other_assignment != ls9.controlled_dca[dca]:
                                self.mix.cues.remove_input_from_dca(cue_num, other_assignment, i)
                                if len(self.mix.cues.get_cue(cue_num).dca[other_assignment]) == 0:
                                    self.mix.cues.set_effects_of_dca(cue_num, other_assignment, [])

                    self.mix.cues.set_input_of_dca(cue_num, ls9.controlled_dca[dca], assignment)
                    self.mix.cues.change_dca_name(cue_num, ls9.controlled_dca[dca], dialog.name.text())
                    effects = []
                    for effect in dialog.fx_select:
                        if dialog.fx_select[effect].isChecked():
                            effects.append(effect)
                    self.mix.cues.set_effects_of_dca(cue_num, ls9.controlled_dca[dca], effects)
                    if self.mix.current_cue == cue_num and self.mix.connected:
                        self.mix.go_cue(cue_num)
                    self.update()
                self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)


class MidiSetupDialog(QDialog):
    def __init__(self, server):
        super().__init__()
        self.server = server
        self.setWindowTitle("Connect to LS9")
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

    def start(self):
        self.server.start()
        self.accept()


class DCAEditDialog(QDialog):
    def __init__(self, parent: LS9MixTableView, index, dca):
        super().__init__(parent=parent)
        self.setWindowTitle("Edit DCA")
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.name = QLineEdit()
        self.name.setText(parent.model.mix.cues.get_cue(index).dca_name[ls9.controlled_dca[dca]])
        self.layout.addWidget(QLabel("CUE Name"))
        self.layout.addWidget(self.name)

        # Double List with Move In (<<) and Move Ou (>>) Buttons, Left is unassigned inputs, right is assigned inputs
        self.dca_layout = QHBoxLayout()
        self.buttons = QVBoxLayout()
        self.unassigned_list = QListWidget()
        self.assigned_list = QListWidget()
        self.move_out = QPushButton("<< Unassign")
        self.move_in = QPushButton(">> Assign")

        self.assignment = parent.model.mix.cues.get_cue(index).dca[ls9.controlled_dca[dca]].copy()
        # Add unsassigned 
        for i in parent.model.mix.controlled_inputs:
            if i not in self.assignment:
                item = QListWidgetItem(parent.model.mix.input_alias[i])
                item.setData(Qt.ItemDataRole.UserRole, i)
                self.unassigned_list.addItem(item)
        
        # Add assigned
        for i in self.assignment:
            item = QListWidgetItem(parent.model.mix.input_alias[i])
            item.setData(Qt.ItemDataRole.UserRole, i)
            self.assigned_list.addItem(item)

        # If they are in any other DCAs in the CUE, set the color to grey and italic
        for i in range(self.unassigned_list.count()):
            for d in ls9.controlled_dca:
                if self.unassigned_list.item(i).data(Qt.ItemDataRole.UserRole) in parent.model.mix.cues.get_cue(index).dca[d]:
                    self.unassigned_list.item(i).setForeground(QColor("#C0C0C0"))
                    self.unassigned_list.item(i).setFont(QFont("Arial", italic=True))
                    break
        
        def move_in():
            selected_items = self.unassigned_list.selectedItems()
            for item in selected_items:
                self.unassigned_list.takeItem(self.unassigned_list.row(item))

                item.setForeground(QColor("#FFFFFF"))
                item.setFont(QFont("Arial", italic=False))

                # Search the position to insert
                for i in range(self.assigned_list.count()):
                    if item.data(Qt.ItemDataRole.UserRole) < self.assigned_list.item(i).data(Qt.ItemDataRole.UserRole):
                        self.assigned_list.insertItem(i, item)
                        break
                else:
                    self.assigned_list.addItem(item)
                self.assigned_list.update()

                # Add the input to the assignment
                self.assignment.append(item.data(Qt.ItemDataRole.UserRole))

        
        def move_out():
            selected_items = self.assigned_list.selectedItems()
            for item in selected_items:
                for d in ls9.controlled_dca:
                    if item.data(Qt.ItemDataRole.UserRole) in parent.model.mix.cues.get_cue(index).dca[d]:
                        item.setForeground(QColor("#C0C0C0"))
                        item.setFont(QFont("Arial", italic=True))
                        break
                self.assigned_list.takeItem(self.assigned_list.row(item))
                
                # Search the position to insert
                for i in range(self.unassigned_list.count()):
                    if item.data(Qt.ItemDataRole.UserRole) < self.unassigned_list.item(i).data(Qt.ItemDataRole.UserRole):
                        self.unassigned_list.insertItem(i, item)
                        break
                else:
                    self.unassigned_list.addItem(item)
                self.unassigned_list.update()

                # Remove the input from the assignment
                self.assignment.remove(item.data(Qt.ItemDataRole.UserRole))
        
        self.move_in.clicked.connect(move_in)
        self.move_out.clicked.connect(move_out)

        # Bind double click
        self.unassigned_list.doubleClicked.connect(move_in)
        self.assigned_list.doubleClicked.connect(move_out)

        self.buttons.addWidget(self.move_in)
        self.buttons.addWidget(self.move_out)
        self.dca_layout.addWidget(self.unassigned_list)
        self.dca_layout.addLayout(self.buttons)
        self.dca_layout.addWidget(self.assigned_list)

        self.layout.addLayout(self.dca_layout)

        # Add FX Select for each FX at the bottom
        self.effect_select_layout = QHBoxLayout()
        self.fx_select = {}
        for effect in parent.mix.effect_ports:
            checkbox = QCheckBox()
            self.fx_select[effect] = checkbox
            self.effect_select_layout.addWidget(QLabel("Effect" + str(effect)))
            self.effect_select_layout.addWidget(checkbox)
            if effect in parent.model.mix.cues.get_cue(index).effects[ls9.controlled_dca[dca]]:
                checkbox.setChecked(True)
            
        self.layout.addLayout(self.effect_select_layout)

        # Add OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.layout.addWidget(self.ok_button)

        # Bind Enter key to OK button
        self.ok_button.setDefault(True)


class SetupWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.server = None
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setWindowTitle("LS9 Mix Server Setup")

        # A Table of 64 Inputs, could select controlled inputs using checkbox and set aias using text field
        self.input_table = QTableWidget(64, 3)
        self.input_table.setHorizontalHeaderLabels(["Input", "Channel", "Alias"])

        self.input_table.verticalHeader().setVisible(False)
        self.input_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        

        # Reduce the width of first two columns
        self.input_table.setColumnWidth(0, 20)
        self.input_table.setColumnWidth(1, 20)

        self.layout.addWidget(self.input_table)
        for i in range(64):
            # Checkbox
            checkbox = QCheckBox()
            self.input_table.setCellWidget(i, 0, checkbox)

            if i < 16:
                checkbox.setChecked(True)

            # Input Number
            self.input_table.setItem(i, 1, QTableWidgetItem(str(i + 1)))

            # Alias
            alias = QLineEdit()
            alias.setText("Mic " + str(i + 1))
            self.input_table.setCellWidget(i, 2, alias)
        
        # Select Effects from 8 Matrixes using Checkbox
        self.effects = QHBoxLayout()
        self.effectcheckboxes = []
        for i in range(8):
            checkbox = QCheckBox()
            self.effects.addWidget(QLabel("Effect" + str(i + 1)))
            self.effects.addWidget(checkbox)
            self.effectcheckboxes.append(checkbox)

            if i == 6 or i == 7:
                checkbox.setChecked(True)
        self.layout.addLayout(self.effects)

        # Add OK button
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.setup_finished)
        self.layout.addWidget(self.ok_button)
    
    def setup_finished(self):
        controlled_inputs = []
        for i in range(64):
            if self.input_table.cellWidget(i, 0).isChecked():
                controlled_inputs.append(i + 1)

        controlled_dca = range(1, 9)

        effect_ports = []
        for i in range(8):
            if self.effectcheckboxes[i].isChecked():
                effect_ports.append(i + 1)
        
        input_alias = {}
        for i in range(64):
            alias = self.input_table.cellWidget(i, 2).text()
            if self.input_table.cellWidget(i, 0).isChecked():
                input_alias[i + 1] = alias

        self.server = ls9.LS9_mix_server(controlled_inputs, controlled_dca, effect_ports, input_alias)


class Ls9MixWidget(QWidget):
    def __init__(self, server, file = None):
        super().__init__()

        self.current_file = file

        # Save Button
        self.save_button = QPushButton("Save")
        def save():
            if self.current_file is None:
                file_name, _ = QFileDialog.getSaveFileName(self, "Save Mix", "", "LS9 Mix Files (*.ls9mix)",)
            else:
                file_name = self.current_file
            if file_name == "":
                return
            self.mix.save(file_name)
        self.save_button.clicked.connect(save)

        # Save As Button
        self.save_as_button = QPushButton("Save As")
        def save_as():
            file_name, _ = QFileDialog.getSaveFileName(self, "Save Mix", "", "LS9 Mix Files (*.ls9mix)",)
            if file_name == "":
                return
            self.mix.save(file_name)
            self.current_file = file_name
        self.save_as_button.clicked.connect(save_as)

        # Load Button
        self.load_button = QPushButton("Load")
        def load():
            file_name, _ = QFileDialog.getOpenFileName(self, "Open Mix", "", "LS9 Mix Files (*.ls9mix)",)
            if file_name == "":
                return
            self.mix.load(file_name)
            self.view.model.beginResetModel()
            self.view.model.endResetModel()
            self.view.update()

            self.current_file = file_name
        self.load_button.clicked.connect(load)

        
        # Show Mode Button
        self.mode_button = QPushButton("Current Mode: Edit Mode")
        self.mode_button.clicked.connect(self.mode_button_clicked)

        # Add CUE button
        self.cue_button = QPushButton("Add CUE")
        def add_cue():
            self.view.model.beginInsertRows(QModelIndex(), len(self.view.model.mix.cues), len(self.view.model.mix.cues))
            if self.view.selectedIndexes() == []:
                self.mix.cues.add_cue()
            else:
                self.mix.cues.add_cue_at(self.view.selectedIndexes()[0].row())
                if self.view.clipboard_mode == 1 and self.view.clipboard > self.view.selectedIndexes()[0].row():
                    self.view.clipboard += 1
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
                if self.view.clipboard_mode == 1 and self.view.clipboard > self.view.selectedIndexes()[0].row():
                    self.view.clipboard += 1
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
            if self.view.clipboard_mode == 1 and self.view.clipboard == selected_row:
                self.view.clipboard_mode = 0
            self.mix.cues.remove_cue(selected_row)
            self.view.model.beginRemoveRows(QModelIndex(), self.view.selectedIndexes()[0].row(), self.view.selectedIndexes()[0].row())
            self.view.model.endRemoveRows()
            self.view.update()
            self.view.selectRow(selected_row)
        self.delete_button.clicked.connect(delete_cue)

        # Connect Console Button
        self.connect_button = QPushButton("Connect Console")
        def connect_console():
            # Open a dialog of midi setup widget
            midi_setup_dialog = MidiSetupDialog(self.server)
            if midi_setup_dialog.exec() == QDialog.DialogCode.Accepted:
                self.connect_button.setText("Connected, Reconnect to Another Port")
        self.connect_button.clicked.connect(connect_console)

        self.control_layout = QHBoxLayout()
        self.control_layout.addWidget(self.save_button)
        self.control_layout.addWidget(self.save_as_button)
        self.control_layout.addWidget(self.load_button)
        # A Vertical Spacer
        self.control_layout.addStretch()
        self.control_layout.addWidget(self.mode_button)
        self.control_layout.addStretch()
        self.control_layout.addWidget(self.cue_button)
        self.control_layout.addWidget(self.duplicate_button)
        self.control_layout.addWidget(self.delete_button)
        self.control_layout.addStretch()
        self.control_layout.addWidget(self.connect_button)
        

        self.control_widget = QWidget()
        self.control_widget.setLayout(self.control_layout)

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(self.control_widget)

        self.server = server
        self.mix = self.server.mix
        self.view = LS9MixTableView(self.mix)
        self.layout.addWidget(self.view)


    def keyPressEvent(self, event):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_S:
                self.ctrl_s()
            elif event.key() == Qt.Key.Key_O:
                self.ctrl_o()
            elif event.key() == Qt.Key.Key_D:
                self.duplicate_button.click()
            elif event.key() == Qt.Key.Key_C or event.key() == Qt.Key.Key_V:
                self.view.keyPressEvent(event)
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier:
            if event.key() == Qt.Key.Key_S:
                self.ctrl_shift_s()

    def ctrl_s(self):
        self.save_button.click()
    
    def ctrl_shift_s(self):
        self.save_as_button.click()
    
    def ctrl_o(self):
        self.load_button.click()
    
    def mode_button_clicked(self):
        if not self.server.enabled:
            self.view.mode = 1
            self.mode_button.setText("Current Mode: Edit Mode")
            return
        if self.view.mode == 0:
            self.view.mode = 1
            self.mode_button.setText("Current Mode: Edit Mode")
        else:
            self.view.mode = 0
            self.mode_button.setText("Current Mode: Show Mode")


class MainWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.main_window = False

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setWindowTitle("LS9 Mix Server")
        self.setup_widget = SetupWidget()
        self.layout.addWidget(self.setup_widget)
        self.setup_widget.ok_button.clicked.connect(self.setup_finished)

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def keyPressEvent(self, event):
        if self.main_window:
            self.ls9_mix_widget.keyPressEvent(event)
    
    def setup_finished(self):
        self.main_window = True

        self.ls9_mix_widget = Ls9MixWidget(self.setup_widget.server)
        self.layout.addWidget(self.ls9_mix_widget)
        print(self.ls9_mix_widget.parent())
        self.setup_widget.hide()
        self.setup_widget.deleteLater()

        # Enable Dark Mode
        qdarktheme.setup_theme()

        self.showMaximized()


if __name__ == '__main__':

    import sys
    import ls9

    app = QApplication([])
    QApplication.setStyle("macos")

    main_widget = MainWidget()
    main_widget.show()
    
    sys.exit(app.exec())