#!/usr/bin/env python3

from time import sleep

import rtmidi
import socket
from threading import Thread, Lock

controlled_inputs = range(33, 49)
controlled_dca = range(1, 9)

effect_ports = (7, 8)
button_next_cue = 1
button_prev_cue = 2

input_alias = {33: 'Mic 1', 34: 'Mic 2', 35: 'Mic 3', 36: 'Mic 4', 37: 'Mic 5', 38: 'Mic 6', 39: 'Mic 7', 40: 'Mic 8', 41: 'Mic 9', 42: 'Mic 10', 43: 'Mic 11', 44: 'Mic 12', 45: 'Mic 13', 46: 'Mic 14', 47: 'Mic 15', 48: 'Mic16'}

mutex = Lock()

class Mix_cue:
    def __init__(self, number, name, dca, effects, dca_name = {}):
        self.number = number
        self.name = name
        self.dca = dca
        self.dca_name = dca_name
        if dca_name == {}:
            for dca in self.dca:
                self.dca_name[dca] = ""
        self.effects = effects
    
    @classmethod
    def from_dict(cls, data):
        return cls(data['number'], data['name'], data['dca'], data['effects'], data['dca_name'])
    
    def copy(self):
        dcas = {}
        for dca in self.dca:
            dcas[dca] = self.dca[dca].copy()
        effects = {}
        for effect in self.effects:
            effects[effect] = self.effects[effect].copy()
        return Mix_cue(self.number, self.name, dcas, effects, self.dca_name.copy())

class Mix_cue_sheet:
    def get_new_cue_number(self):
        number = float(self.cues[-1].number)

        # Get the next integer
        return str(int(number) + 1)

    def generate_blank_cue(self, number = '', name = ''):
        if number == '':
            number = self.get_new_cue_number()
        
        return Mix_cue(number, name, {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}, {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []})

    def __init__(self, controlled_inputs, controlled_dca, effect_ports):
        self.controlled_inputs = controlled_inputs
        self.controlled_dca = controlled_dca
        self.effect_ports = effect_ports

        self.cues = [
            self.generate_blank_cue('0', 'Line Check')
        ]

        # Magic Numbers
        self.dca_assignment_header = 0x11
        self.effect_assignment_header = 0x12
        self.dca_name_header = 0x13
        self.count_header = 3
    
    def add_cue(self):
        self.cues.append(self.generate_blank_cue())
        return True

    def add_cue_at(self, index):
        if index < 0 or index >= len(self.cues):
            return False
        if index == len(self.cues) - 1:
            return self.add_cue()
        prev_num = float(self.cues[index].number)
        next_num = float(self.cues[index + 1].number)
        if int(prev_num) + 1 < next_num:
            new_num = str(int(prev_num) + 1)
        else:
            new_num = str((prev_num + next_num) / 2)
        new_cue = self.generate_blank_cue()
        new_cue.number = new_num
        self.cues.insert(index + 1, new_cue)
        return True
    
    def duplicate_cue(self, index):
        if index < 0 or index >= len(self.cues):
            return False
        new_cue = self.cues[index].copy()
        if index == len(self.cues) - 1:
            new_cue.number = self.get_new_cue_number()
        else:
            prev_num = float(self.cues[index].number)
            next_num = float(self.cues[index + 1].number)
            if int(prev_num) + 1 < next_num:
                new_num = str(int(prev_num) + 1)
            else:
                new_num = str((prev_num + next_num) / 2)
            new_cue.number = new_num
        self.cues.insert(index + 1, new_cue)
        return True
    
    def copy_cue(self, index):
        if index < 0 or index >= len(self.cues):
            return False
        new_cue = self.cues[index].copy()
        new_cue.number = self.get_new_cue_number()
        self.cues.append(self.cues[index].copy())
        return True
    
    def copy_cue_to(self, index, target_index):
        if index < 0 or index >= len(self.cues):
            return False
        if target_index < 0 or target_index >= len(self.cues):
            return False
        new_cue = self.cues[index].copy()

        if target_index == len(self.cues) - 1:
            new_cue.number = self.get_new_cue_number()
        else:
            prev_num = float(self.cues[target_index].number)
            next_num = float(self.cues[target_index + 1].number)
            if int(prev_num) + 1 < next_num:
                new_num = str(int(prev_num) + 1)
            else:
                new_num = str((prev_num + next_num) / 2)
            new_cue.number = new_num

        self.cues.insert(target_index + 1, new_cue)
        return True
    
    def remove_cue(self, index):
        if index <= 0 or index >= len(self.cues):
            return False
        self.cues.pop(index)
        return True
    
    def add_input_to_dca(self, index, dca, input):
        if index < 0 or index >= len(self.cues):
            return False
        if input not in self.controlled_inputs:
            return False
        if dca not in self.controlled_dca:
            return False
        for dca in self.controlled_dca:
            if input in self.cues[index].dca[dca]:
                self.cues[index].dca[dca].remove(input)
        self.cues[index].dca[dca].append(input)
        return True
    
    def remove_input_from_dca(self, index, dca, input):
        if index < 0 or index >= len(self.cues):
            return False
        if index < 0 or index >= len(self.cues):
            return False
        if input not in self.controlled_inputs:
            return False
        if dca not in self.controlled_dca:
            return False
        if input in self.cues[index].dca[dca]:
            self.cues[index].dca[dca].remove(input)
            return True
        return False

    def set_input_of_dca(self, index, dca, inputs):
        if index < 0 or index >= len(self.cues):
            return False
        if dca not in self.controlled_dca:
            return False
        self.cues[index].dca[dca] = inputs
        return True
    
    def change_dca_name(self, index, dca, name):
        if index < 0 or index >= len(self.cues):
            return False
        if dca not in self.controlled_dca:
            return False
        self.cues[index].dca_name[dca] = name
        return True
    
    def change_name(self, index, name):
        if index < 0 or index >= len(self.cues):
            return False
        self.cues[index].name = name
        return True

    def change_number(self, index, number):
        if index < 0 or index >= len(self.cues):
            return False
        # Check if the number is larger than the number of next cue
        if index < len(self.cues) - 1 and float(number) > float(self.cues[index + 1].number):
            return False
        if index > 0 and float(number) < float(self.cues[index - 1].number):
            return False
        self.cues[index].number = str(number)
        return True
    
    def add_effect_to_dca(self, index, dca, effect):
        if index < 0 or index >= len(self.cues):
            return False
        if effect not in self.effect_ports:
            return False
        if dca not in self.controlled_dca:
            return False
        if effect not in self.cues[index].effects[dca]:
            self.cues[index].effects[dca].append(effect)
            return True
        return False
    
    def remove_effect_from_dca(self, index, dca, effect):
        if index < 0 or index >= len(self.cues):
            return False
        if effect not in self.effect_ports:
            return False
        if dca not in self.controlled_dca:
            return False
        if effect in self.cues[index].effects[dca]:
            self.cues[index].effects[dca].remove(effect)
            return True
        return False
    
    def set_effects_of_dca(self, index, dca, effects):
        if index < 0 or index >= len(self.cues):
            return False
        if dca not in self.controlled_dca:
            return False
        self.cues[index].effects[dca] = effects
        return True
    
    def get_cue(self, index):
        if index < 0 or index >= len(self.cues):
            return None
        return self.cues[index]
    
    def __len__(self):
        return len(self.cues)

    def to_array(self):
        data = []
        for cue in self.cues:
            data.append({
                'number': cue.number,
                'name': cue.name,
                'dca': cue.dca,
                'effects': cue.effects,
                'dca_name': cue.dca_name
            })
        return data
    
    def load_array(self, data):
        self.cues = []
        for cue in data:
            if 'name' not in cue:
                cue['name'] = ''
            if 'dca_name' not in cue:
                cue['dca_name'] = {}
            self.cues.append(Mix_cue.from_dict(cue))
    
    def to_binary(self):
        """
        Generate binary data for the cue sheet
        Structure: 
        Number of cues (4 bytes)
        For each cue:
            Length of the cue number (2 bytes)
            Cue number (variable length)
            Length of the cue name (2 bytes)
            Cue name (variable length)
            Count of Blocks (1 byte)
            --------------------------
            Block Length (2 bytes)
            Block Magic (1 byte)
            Block Content (variable length)

        Block includes:
            DCA Assignment
            Effect Assignment
            DCA Name
        
        DCA Assignment:
            For each DCA:
                Length of the DCA Assignment (1 byte)
                For each input:
                    Input Number (1 byte)
        
        Effect Assignment:
            For each DCA:
                Length of the Effect Assignment (1 byte)
                For each effect:
                    Effect Number (1 byte)
        
        DCA Name:
            For each DCA:
                Length of the DCA Name (2 bytes)
                DCA Name (variable length)
        """
        binrary_data = b'' # Data without the length
        

        binrary_data += len(self.cues).to_bytes(4, 'big')
        for cue in self.cues:
            binrary_data += len(cue.number).to_bytes(2, 'big')
            binrary_data += cue.number.encode('utf-8')
            binrary_data += len(cue.name).to_bytes(2, 'big')
            binrary_data += cue.name.encode('utf-8')
            binrary_data += self.count_header.to_bytes(1, 'big')
            
            dca_block = b''
            dca_block += self.dca_assignment_header.to_bytes(1, 'big')
            for dca in self.controlled_dca:
                dca_block += len(cue.dca[dca]).to_bytes(1, 'big')
                for input in cue.dca[dca]:
                    dca_block += input.to_bytes(1, 'big')
            dca_length = len(dca_block) + 2
            binrary_data += dca_length.to_bytes(2, 'big')
            binrary_data += dca_block

            effect_block = b''
            effect_block += self.effect_assignment_header.to_bytes(1, 'big')
            for dca in self.controlled_dca:
                effect_block += len(cue.effects[dca]).to_bytes(1, 'big')
                for effect in cue.effects[dca]:
                    effect_block += effect.to_bytes(1, 'big')
            effect_length = len(effect_block) + 2
            binrary_data += effect_length.to_bytes(2, 'big')
            binrary_data += effect_block

            dca_name_block = b''
            dca_name_block += self.dca_name_header.to_bytes(1, 'big')
            for dca in self.controlled_dca:
                dca_name_block += len(cue.dca_name[dca]).to_bytes(2, 'big')
                dca_name_block += cue.dca_name[dca].encode('utf-8')
            dca_name_length = len(dca_name_block) + 2
            binrary_data += dca_name_length.to_bytes(2, 'big')
            binrary_data += dca_name_block

        return binrary_data

    def load_binary(self, controlled_inputs, controlled_dca, effect_ports, data):
        self.controlled_inputs = controlled_inputs
        self.controlled_dca = controlled_dca
        self.effect_ports = effect_ports

        cue_count = int.from_bytes(data[0:4], 'big')
        data = data[4:]

        self.cues = []
        for i in range(cue_count):
            # Read the cue number
            cue_number_len = int.from_bytes(data[0:2], 'big')
            cue_number = data[2:2 + cue_number_len].decode('utf-8')
            data = data[2 + cue_number_len:]

            # Read the cue name
            cue_name_len = int.from_bytes(data[0:2], 'big')
            cue_name = data[2:2 + cue_name_len].decode('utf-8')
            data = data[2 + cue_name_len:]

            # Read the count of blocks
            block_count = data[0]
            data = data[1:]

            # Read the blocks
            dca_assignment = {}
            effect_assignment = {}
            dca_name = {}
            for i in range(block_count):
                block_length = int.from_bytes(data[0:2], 'big')
                block_data = data[2:block_length]
                data = data[block_length:]

                block_magic = block_data[0]
                block_data = block_data[1:]

                if block_magic == self.dca_assignment_header:
                    dca_assignment = {}
                    for dca in self.controlled_dca:
                        dca_assignment[dca] = []
                        dca_len = block_data[0]
                        block_data = block_data[1:]
                        for i in range(dca_len):
                            dca_assignment[dca].append(block_data[0])
                            block_data = block_data[1:]
                elif block_magic == self.effect_assignment_header:
                    effect_assignment = {}
                    for dca in self.controlled_dca:
                        effect_assignment[dca] = []
                        effect_len = block_data[0]
                        block_data = block_data[1:]
                        for i in range(effect_len):
                            effect_assignment[dca].append(block_data[0])
                            block_data = block_data[1:]
                elif block_magic == self.dca_name_header:
                    dca_name = {}
                    for dca in self.controlled_dca:
                        dca_name[dca] = ''
                        dca_len = int.from_bytes(block_data[0:2], 'big')
                        block_data = block_data[2:]
                        dca_name[dca] = block_data[0:dca_len].decode('utf-8')
                        block_data = block_data[dca_len:]
                        dca_name[dca] = block_data[0:dca_len].decode('utf-8')
                    
            self.cues.append(Mix_cue(cue_number, cue_name, dca_assignment, effect_assignment, dca_name))

    @classmethod
    def from_array(cls, controlled_inputs, controlled_dca, effect_ports, data):
        cue_sheet = cls(controlled_inputs, controlled_dca, effect_ports)
        cue_sheet.cues = []
        for cue in data:
            if 'name' not in cue:
                cue['name'] = ''
            if 'dca_name' not in cue:
                cue['dca_name'] = {}
            cue_sheet.cues.append(Mix_cue.from_dict(cue))
        return cue_sheet

class LS9_NRPN_Sender:
    def __init__(self, midi_out, channel):
        self.midi_out = midi_out
        self.head = 0xb0 | channel
    
    def send_input_on(self, channel):
        base = 0x05b6
        if channel < 49:
            base += channel - 1
        else:
            base += channel - 1 + 8
        self.midi_out.send_message((self.head, 0x63, base >> 7))
        self.midi_out.send_message((self.head, 0x62, base & 0x7f))
        self.midi_out.send_message((self.head, 0x06, 0x7f))
    
    def send_input_off(self, channel):
        base = 0x05b6
        if channel < 49:
            base += channel - 1
        else:
            base += channel - 1 + 8
        self.midi_out.send_message((self.head, 0x63, base >> 7))
        self.midi_out.send_message((self.head, 0x62, base & 0x7f))
        self.midi_out.send_message((self.head, 0x06, 0x00))

    def send_input_to_mix_on(self, channel, mix):
        if channel < 57:
            base = 0x2c30
            base += (mix - 1) * 64 + channel - 1
        else:
            base = 0x112a
            base += (mix - 1) * 8 + channel - 57
        self.midi_out.send_message((self.head, 0x63, base >> 7))
        self.midi_out.send_message((self.head, 0x62, base & 0x7f))
        self.midi_out.send_message((self.head, 0x06, 0x7f))

    def send_input_to_mix_off(self, channel, mix):
        if channel < 57:
            base = 0x2c30
            base += (mix - 1) * 64 + channel - 1
        else:
            base = 0x112a
            base += (mix - 1) * 8 + channel - 57
        self.midi_out.send_message((self.head, 0x63, base >> 7))
        self.midi_out.send_message((self.head, 0x62, base & 0x7f))
        self.midi_out.send_message((self.head, 0x06, 0x00))

    def send_output_to_matrix_on(self, mix, matrix):
        base = 0x0ab4
        base += (matrix - 1) * 22 + mix - 1
        self.midi_out.send_message((self.head, 0x63, base >> 7))
        self.midi_out.send_message((self.head, 0x62, base & 0x7f))
        self.midi_out.send_message((self.head, 0x06, 0x7f))

    def send_output_to_matrix_off(self, mix, matrix):
        base = 0x0ab4
        base += (matrix - 1) * 22 + mix - 1
        self.midi_out.send_message((self.head, 0x63, base >> 7))
        self.midi_out.send_message((self.head, 0x62, base & 0x7f))
        self.midi_out.send_message((self.head, 0x06, 0x00))

class LS9_SysEx_Sender:
    def __init__(self, midi_out, channel):
        self.midi_out = midi_out
        self.head = 0xf0
        self.tail = 0xf7
    
    def send_input_on(self, channel):
        # 240 67 16 62 18 1 0 49 0 0 0 channel 0 0 0 0 ON/OFF 247
        self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 49, 0, 0, 0, channel - 1, 0, 0, 0, 0, 1, self.tail))
    
    def send_input_off(self, channel):
        # 240 67 16 62 18 1 0 49 0 0 0 channel 0 0 0 0 ON/OFF 247
        self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 49, 0, 0, 0, channel - 1, 0, 0, 0, 0, 0, self.tail))
    
    def send_input_to_mix_on(self, channel, mix):
        # 240 67 16 62 18 1 0 67 0 3*mix 0 channel 0 0 0 0 ON/OFF 247
        self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 67, 0, 3 * mix - 3, 0, channel - 1, 0, 0, 0, 0, 1, self.tail))
    
    def send_input_to_mix_off(self, channel, mix):
        # 240 67 16 62 18 1 0 67 0 3*mix 0 channel 0 0 0 0 ON/OFF 247
        self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 67, 0, 3 * mix - 3, 0, channel - 1, 0, 0, 0, 0, 0, self.tail))
    
    def send_output_to_matrix_on(self, mix, matrix):
        # 240 67 16 62 18 1 0 85 0 3*matrix 0 mix 0 0 0 0 ON/OFF 247
        self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 85, 0, 3 * matrix - 3, 0, mix - 1, 0, 0, 0, 0, 1, self.tail))
    
    def send_output_to_matrix_off(self, mix, matrix):
        # 240 67 16 62 18 1 0 85 0 3*matrix 0 mix 0 0 0 0 ON/OFF 247
        self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 85, 0, 3 * matrix - 3, 0, mix - 1, 0, 0, 0, 0, 0, self.tail))
    
    def send_mix_pan(self, mix, pan):
        if pan > 0:
            # 240 67 16 62 18 1 0 87 0 2 0 mix 0 0 0 0 0 pan 247
            self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 87, 0, 2, 0, mix - 1, 0, 0, 0, 0, 0, pan, self.tail))
        else:
            # 240 67 16 62 18 1 0 87 0 2 0 0 15 127 127 127 128 - pan 247
            self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 87, 0, 2, 0, 0, 15, 127, 127, 127, 128 - pan, self.tail))
    
    def send_input_pan(self, input, pan):
        if pan > 0:
            # 240 67 16 62 18 1 0 50 0 1 0 input 0 0 0 0 0 pan 247
            self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 50, 0, 1, 0, input - 1, 0, 0, 0, 0, 0, pan, self.tail))
        else:
            # 240 67 16 62 18 1 0 50 0 1 0 0 15 127 127 127 128 - pan 247
            self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 50, 0, 1, 0, 0, 15, 127, 127, 127, 128 - pan, self.tail))
    
    def link_mix(self, mix):
        # 240 67 16 62 18 1 0 34 0 0 0 mix 0 0 0 0 UNLINK/LINK 247
        self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 34, 0, 0, 0, mix - 1, 0, 0, 0, 0, 1, self.tail))

    def unlink_mix(self, mix):
        # 240 67 16 62 18 1 0 34 0 0 0 mix 0 0 0 0 UNLINK/LINK 247
        self.midi_out.send_message((self.head, 67, 16, 62, 18, 1, 0, 34, 0, 0, 0, mix - 1, 0, 0, 0, 0, 0, self.tail))
    
class LS9_mix:
    def __init__(self, midi_sender, controlled_inputs, controlled_dca, effect_ports, input_alias, cues):
        self.midi_sender = midi_sender
        self.controlled_inputs = controlled_inputs
        self.controlled_dca = controlled_dca
        self.effect_ports = effect_ports
        self.input_alias = input_alias
        self.input_groups = {'ALL': controlled_inputs.copy(), 'Male': [], 'Female': []}

        self.connected = False
        
        self.cues = cues
        self.current_cue = 0 # 0 is line-check

        self.event_callbacks = []

        # Magic Numbers
        self.overall_magic = 'LS9M'.encode('utf-8')
        self.controlled_inputs_magic = 0x01
        self.controlled_dca_magic = 0x02
        self.effect_ports_magic = 0x03
        self.input_alias_magic = 0x04
        self.cue_data_magic = 0x05
        self.input_group_magic = 0x06

    def send_initialize(self):
        for input in self.controlled_inputs:
            for dca in self.controlled_dca:
                self.midi_sender.send_input_to_mix_off(input, dca)
            self.midi_sender.send_input_off(input)
        
        for dca in self.controlled_dca:
            for effect in self.effect_ports:
                self.midi_sender.send_output_to_matrix_off(dca, effect)
        
        self.channel_on = {}
        for input in self.controlled_inputs:
            self.channel_on[input] = 0
        
        self.dca = {}
        self.effects = {}
        for dca in self.controlled_dca:
            self.dca[dca] = []
            self.effects[dca] = []

        self.go_cue(0)

    def _go_cue(self, target_cue_idx):
        target_cue = self.cues.get_cue(target_cue_idx)
        channel_on = {}
        for dca in self.controlled_dca:
            current_assignment = target_cue.dca[dca]
            last_assignment = self.dca[dca]
            for input in current_assignment:
                if input not in last_assignment:
                    self.midi_sender.send_input_to_mix_on(input, dca)
            for input in last_assignment:
                if input not in current_assignment:
                    self.midi_sender.send_input_to_mix_off(input, dca)
            self.dca[dca] = current_assignment.copy()
            for input in current_assignment:
                channel_on[input] = 1
            for effect in self.effects[dca]:
                if effect not in target_cue.effects[dca]:
                    self.midi_sender.send_output_to_matrix_off(dca, effect)
            for effect in target_cue.effects[dca]:
                if effect not in self.effects[dca]:
                    self.midi_sender.send_output_to_matrix_on(dca, effect)
            self.effects[dca] = target_cue.effects[dca]
        for input in self.controlled_inputs:
            if input in channel_on and input not in self.channel_on:
                self.midi_sender.send_input_on(input)
            if input in self.channel_on and input not in channel_on:
                self.midi_sender.send_input_off(input)
        self.channel_on = channel_on

    def go_cue(self, target_cue_idx):
        if not self.connected:
            return
        mutex.acquire()
        self.current_cue = target_cue_idx
        self._go_cue(target_cue_idx)
        mutex.release()
        for callback in self.event_callbacks:
            callback(self.current_cue)
    
    def next_cue(self):
        if not self.connected:
            return
        mutex.acquire()
        self.current_cue += 1
        if self.current_cue >= len(self.cues):
            self.current_cue -= 1
        self._go_cue(self.current_cue)
        mutex.release()
        for callback in self.event_callbacks:
            callback(self.current_cue)
    
    def previous_cue(self):
        if not self.connected:
            return
        mutex.acquire()
        self.current_cue -= 1
        if self.current_cue < 0:
            self.current_cue = 0
        self._go_cue(self.current_cue)
        mutex.release()
        for callback in self.event_callbacks:
            callback(self.current_cue)
    
    def register_event_callback(self, callback):
        self.event_callbacks.append(callback)

    def save(self, filename):
        """
        Save the current state to the file
        Structure:
        Overall Magic (4 bytes)
        --------
        Block Length (4 bytes)
        Block Magic (1 byte)
        Block Content (variable length)

        Block Content:
        Controlled Inputs
        Controlled DCA
        Effect Ports
        Input Alias
        Input Groups
        Cue Data

        Controlled Inputs:
        Length of the controlled inputs (1 byte)
        For each input:
            Input Number (1 byte)
        
        Controlled DCA:
        Length of the controlled DCA (1 byte)
        For each DCA:
            DCA Number (1 byte)
        
        Effect Ports:
        Length of the effect ports (1 byte)
        For each effect port:
            Effect Port Number (1 byte)
        
        Input Alias:
        Length of the input alias (1 byte)
        For each input:
            Input Number (2 bytes)
            Length of the alias (1 byte)
            Alias (variable length)
        
        Input Groups:
        Length of the input groups (1 byte)
        For each group:
            Length of the group name (1 byte)
            Group Name (variable length)
            Length of the group members (1 byte)
            For each member:
                Member Number (1 byte)
        
        Cue Data:
        Realization in the Mix_cue_sheet.to_binary()
        """
        binary_data = b''

        binary_data += self.overall_magic
        controlled_inputs_data = b''
        controlled_inputs_data += len(self.controlled_inputs).to_bytes(1, 'big')
        for input in self.controlled_inputs:
            controlled_inputs_data += input.to_bytes(1, 'big')
        controlled_inputs_len = len(controlled_inputs_data) + 5
        binary_data += controlled_inputs_len.to_bytes(4, 'big')
        binary_data += self.controlled_inputs_magic.to_bytes(1, 'big')
        binary_data += controlled_inputs_data

        controlled_dca_data = b''
        controlled_dca_data += len(self.controlled_dca).to_bytes(1, 'big')
        for dca in self.controlled_dca:
            controlled_dca_data += dca.to_bytes(1, 'big')
        controlled_dca_len = len(controlled_dca_data) + 5
        binary_data += controlled_dca_len.to_bytes(4, 'big')
        binary_data += self.controlled_dca_magic.to_bytes(1, 'big')
        binary_data += controlled_dca_data

        effect_ports_data = b''
        effect_ports_data += len(self.effect_ports).to_bytes(1, 'big')
        for effect in self.effect_ports:
            effect_ports_data += effect.to_bytes(1, 'big')
        effect_ports_len = len(effect_ports_data) + 5
        binary_data += effect_ports_len.to_bytes(4, 'big')
        binary_data += self.effect_ports_magic.to_bytes(1, 'big')
        binary_data += effect_ports_data

        input_alias_data = b''
        input_alias_data += len(self.input_alias).to_bytes(1, 'big')
        for input in self.input_alias:
            input_alias_data += input.to_bytes(2, 'big')
            alias = self.input_alias[input]
            input_alias_data += len(alias).to_bytes(1, 'big')
            input_alias_data += alias.encode('utf-8')
        input_alias_len = len(input_alias_data) + 5
        binary_data += input_alias_len.to_bytes(4, 'big')
        binary_data += self.input_alias_magic.to_bytes(1, 'big')
        binary_data += input_alias_data

        input_group_data = b''
        input_group_data += len(self.input_groups).to_bytes(1, 'big')
        for group in self.input_groups:
            input_group_data += len(group).to_bytes(1, 'big')
            input_group_data += group.encode('utf-8')
            input_group_data += len(self.input_groups[group]).to_bytes(1, 'big')
            for member in self.input_groups[group]:
                input_group_data += member.to_bytes(1, 'big')
        input_group_len = len(input_group_data) + 5
        binary_data += input_group_len.to_bytes(4, 'big')
        binary_data += self.input_group_magic.to_bytes(1, 'big')
        binary_data += input_group_data

        mutex.acquire()
        cue_data = self.cues.to_binary()
        mutex.release()
        cue_data_len = len(cue_data) + 5
        binary_data += cue_data_len.to_bytes(4, 'big')
        binary_data += self.cue_data_magic.to_bytes(1, 'big')
        binary_data += cue_data

        with open(filename, 'wb') as file:
            file.write(binary_data)
    
    def load(self, filename):
        with open(filename, 'rb') as file:
            binary_data = file.read()
        
        if binary_data[0:4] != self.overall_magic:
            return False
        binary_data = binary_data[4:]

        while len(binary_data) > 0:
            # Read the block length
            block_length = int.from_bytes(binary_data[0:4], 'big')

            # Read the whole block
            block_data = binary_data[4:block_length]

            # Remove the block from the binary data
            binary_data = binary_data[block_length:]

            # Read the block magic
            block_magic = int.from_bytes(block_data[0:1], 'big')
            block_data = block_data[1:]

            if block_magic == self.controlled_inputs_magic:
                controlled_inputs = []
                controlled_inputs_len = block_data[0]
                block_data = block_data[1:]
                for i in range(controlled_inputs_len):
                    controlled_inputs.append(block_data[i])
            elif block_magic == self.controlled_dca_magic:
                controlled_dca = []
                controlled_dca_len = block_data[0]
                block_data = block_data[1:]
                for i in range(controlled_dca_len):
                    controlled_dca.append(block_data[i])
            elif block_magic == self.effect_ports_magic:
                effect_ports = []
                effect_ports_len = block_data[0]
                block_data = block_data[1:]
                for i in range(effect_ports_len):
                    effect_ports.append(block_data[i])
            elif block_magic == self.input_alias_magic:
                input_alias = {}
                input_alias_len = int.from_bytes(block_data[0:1], 'big')
                block_data = block_data[1:]
                for i in range(input_alias_len):
                    input = int.from_bytes(block_data[0:2], 'big')
                    block_data = block_data[2:]
                    alias_len = block_data[0]
                    block_data = block_data[1:]
                    alias = block_data[0:alias_len].decode('utf-8')
                    block_data = block_data[alias_len:]
                    input_alias[input] = alias
            elif block_magic == self.cue_data_magic:
                mutex.acquire()
                self.cues.load_binary(controlled_inputs, controlled_dca, effect_ports, block_data)
                mutex.release()
            elif block_magic == self.input_group_magic:
                input_group = {'ALL': self.controlled_inputs}
                input_group_len = block_data[0]
                block_data = block_data[1:]
                for i in range(input_group_len):
                    group_len = block_data[0]
                    block_data = block_data[1:]
                    group = block_data[0:group_len].decode('utf-8')
                    block_data = block_data[group_len:]
                    input_group[group] = []
                    member_len = block_data[0]
                    block_data = block_data[1:]
                    for i in range(member_len):
                        input_group[group].append(block_data[0])
                        block_data = block_data[1:]
                self.input_groups = input_group
        
        mutex.acquire()
        self.controlled_inputs = controlled_inputs
        self.controlled_dca = controlled_dca
        self.effect_ports = effect_ports
        self.input_alias = input_alias
        self.current_cue = 0 # 0 is line-check
        mutex.release()
        if self.connected:
            self.send_initialize()

class OSC_server():
    def __init__(self, port):
        # Establish UDP Socket server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('localhost', port))
    
    def listen(self):
        try:
            data, addr = self.sock.recvfrom(1024)
            return data
        except socket.timeout:
            return None

def generate_nrpn_callback_function(nrpn_parser):
    address = 0
    value = 0
    state = 0
    def midi_callback(message, time):
        nonlocal address
        nonlocal value
        nonlocal state
        message = message[0]
        if message[0] == 0xb0:
            if message[1] == 0x63:
                address += message[2] << 7
                state += 1
                if state >= 3:
                    address = message[2] << 7
                    state = 1
            elif message[1] == 0x62:
                address += message[2]
                state += 1
                if state >= 3:
                    address = message[2]
                    state = 1
            elif message[1] == 0x06 and (state == 2 or state == 3):
                value += message[2]
                state += 1
            elif message[1] == 0x26 and (state == 2 or state == 3):
                value += message[2] << 7
                state += 1
        if state == 4:
            nrpn_parser(address, value)
            address = 0
            value = 0
            state = 0
    return midi_callback

def generate_sysex_callback_function(sysex_parser):
    def midi_callback(message, time):
        message = message[0]
        if message[0] == 0xf0:
            sysex_parser(message)
    return midi_callback

def generate_nrpn_parser(ls9_mix):
    def parse_nrpn_input(address, value):
        if address >= 0x3a5a and address <= 0x3a61:
            # Mute Master
            if address - 0x3a5a + 1 == button_next_cue:
                ls9_mix.next_cue()
            elif address - 0x3a5a + 1 == button_prev_cue:
                ls9_mix.previous_cue()
    return parse_nrpn_input

def generate_sysex_parser(ls9_mix):
    # 240, 67, 16, 62, 18, 1, 2, 57, 0, 53, 0, 0, 0, 0, 0, 8, 0, 247 - Next
    # 240, 67, 16, 62, 18, 1, 2, 57, 0, 53, 0, 0, 0, 0, 0, 16, 0, 247 - Previous
    # Exact Match
    def parse_sysex_input(message):
        if message == [240, 67, 16, 62, 18, 1, 2, 57, 0, 53, 0, 0, 0, 0, 0, 8, 0, 247]:
            ls9_mix.next_cue()
        elif message == [240, 67, 16, 62, 18, 1, 2, 57, 0, 53, 0, 0, 0, 0, 0, 16, 0, 247]:
            ls9_mix.previous_cue()
    
    return parse_sysex_input


class LS9_mix_server():
    def __init__(self, controlled_inputs = controlled_inputs, controlled_dca = controlled_dca, effect_ports = effect_ports, input_alias = input_alias):
        self.midi_in = rtmidi.MidiIn()
        self.midi_in.ignore_types(sysex=False)
        self.midi_out = rtmidi.MidiOut()
        self.ls9 = LS9_NRPN_Sender(self.midi_out, 0)
        self.mix = LS9_mix(self.ls9, controlled_inputs, controlled_dca, effect_ports, input_alias, Mix_cue_sheet.from_array(controlled_inputs, controlled_dca, effect_ports, [
            {'number': '0', 'name': 'Line Check', 'dca': {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}, 'effects': {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}}
            ]))   
        self.osc_server = OSC_server(53001)
        self.enabled = False

    def get_midi_in_ports(self):
        return self.midi_in.get_ports()

    def get_midi_out_ports(self):
        return self.midi_out.get_ports()

    def set_midi_in_port(self, idx):
        self.midi_in.open_port(idx)

    def set_midi_out_port(self, idx):
        self.midi_out.open_port(idx)

    def start(self):
        # Test Sysex
        sysex = False
        def sysex_tester(message, time):
            message = message[0]
            if message == [240, 67, 16, 62, 18, 127, 247]:
                nonlocal sysex
                sysex = True

        self.midi_in.set_callback(sysex_tester)
        sleep(1)
        if not sysex:
            self.midi_in.set_callback(generate_nrpn_callback_function(generate_nrpn_parser(self.mix)))
        else:
            self.midi_in.set_callback(generate_sysex_callback_function(generate_sysex_parser(self.mix)))
            self.mix.midi_sender = LS9_SysEx_Sender(self.midi_out, 0)

        self.enabled = True     
        self.mix.connected = True     

        self.mix.send_initialize()

        def socket_poll():
            while 1:
                data = self.osc_server.listen()
                
                # Truncate the message to the first 0
                data = data[:data.index(0)]
                if data == b'/next':
                    self.mix.next_cue()
                elif data == b'/prev':
                    self.mix.previous_cue()

                # Process go cues
                if data[:4] == b'/go/':
                    cue = int(data[4:])
                    self.mix.go_cue(cue)

        Thread(target=socket_poll, daemon=True).start()                                                                               


if __name__ == "__main__":
    server = LS9_mix_server()
    available_ports = server.get_midi_in_ports()
    for idx, port in enumerate(available_ports):
        if 'USB' in port:
            server.set_midi_in_port(idx)
            break
    available_ports = server.get_midi_out_ports()
    for idx, port in enumerate(available_ports):
        if 'USB' in port:
            server.set_midi_out_port(idx)
            break
    server.start()