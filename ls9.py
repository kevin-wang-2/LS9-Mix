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
        return Mix_cue(self.number, self.name, dcas, effects)

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

class LS9_mix:
    def __init__(self, NRPN, controlled_inputs, controlled_dca, effect_ports, input_alias, cues):
        self.NRPN = NRPN
        self.controlled_inputs = controlled_inputs
        self.controlled_dca = controlled_dca
        self.effect_ports = effect_ports
        self.input_alias = input_alias

        self.connected = False
        
        self.cues = cues
        self.current_cue = 0 # 0 is line-check

        self.event_callbacks = []

    def send_initialize(self):
        for input in self.controlled_inputs:
            for dca in self.controlled_dca:
                self.NRPN.send_input_to_mix_off(input, dca)
            self.NRPN.send_input_off(input)
        
        for dca in self.controlled_dca:
            for effect in self.effect_ports:
                self.NRPN.send_output_to_matrix_off(dca, effect)
        
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
                    self.NRPN.send_input_to_mix_on(input, dca)
            for input in last_assignment:
                if input not in current_assignment:
                    self.NRPN.send_input_to_mix_off(input, dca)
            for input in current_assignment:
                channel_on[input] = 1
            for effect in self.effects[dca]:
                if effect not in target_cue.effects[dca]:
                    self.NRPN.send_output_to_matrix_off(dca, effect)
            for effect in target_cue.effects[dca]:
                if effect not in self.effects[dca]:
                    self.NRPN.send_output_to_matrix_on(dca, effect)
            self.effects[dca] = target_cue.effects[dca]
        for input in self.controlled_inputs:
            if input in channel_on and input not in self.channel_on:
                self.NRPN.send_input_on(input)
            if input in self.channel_on and input not in channel_on:
                self.NRPN.send_input_off(input)
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
        mutex.acquire()
        data = self.cues.to_array()
        mutex.release()

        binary_data = b''

        # 1. Save the amount of controlled inputs
        binary_data += len(self.controlled_inputs).to_bytes(1, 'big')

        # 2. Save the controlled inputs
        for input in self.controlled_inputs:
            binary_data += input.to_bytes(1, 'big')
        
        # 3. Save the amount of controlled dca
        binary_data += len(self.controlled_dca).to_bytes(1, 'big')

        # 4. Save the controlled dca
        for dca in self.controlled_dca:
            binary_data += dca.to_bytes(1, 'big')

        # 5. Save the amount of effect ports
        binary_data += len(self.effect_ports).to_bytes(1, 'big')
        for effect in self.effect_ports:
            binary_data += effect.to_bytes(1, 'big')

        # 6. Save input alias
        binary_data += len(self.input_alias).to_bytes(1, 'big')
        for input in self.input_alias:
            binary_data += input.to_bytes(2, 'big')
            binary_data += len(self.input_alias[input]).to_bytes(1, 'big')
            binary_data += self.input_alias[input].encode('utf-8')
        
        # 7. Save the cue data

        # 7.1. Save the amount of cues
        binary_data += len(data).to_bytes(4, 'big')

        for cue in data:
            # 7.2 save the length of the cue number and the cue number
            cue['number'] = str(cue['number'])
            binary_data += len(cue['number']).to_bytes(2, 'big')
            binary_data += cue['number'].encode('utf-8')

            # 7.3 save the length of the cue name and the cue name
            binary_data += len(cue['name']).to_bytes(2, 'big')
            binary_data += cue['name'].encode('utf-8')

            # 7.4 Save each controlled dca
            for dca in self.controlled_dca:
                binary_data += len(cue['dca'][dca]).to_bytes(1, 'big')
                for input in cue['dca'][dca]:
                    binary_data += input.to_bytes(1, 'big')
            
            # 7.5 Save each effect port
            for dca in self.controlled_dca:
                binary_data += len(cue['effects'][dca]).to_bytes(1, 'big')
                for effect in cue['effects'][dca]:
                    binary_data += effect.to_bytes(1, 'big')

            # 7.6 Save the dca names
            for dca in self.controlled_dca:
                binary_data += len(cue['dca_name'][dca]).to_bytes(2, 'big')
                binary_data += cue['dca_name'][dca].encode('utf-8')
            
        with open(filename, 'wb') as file:
            file.write(binary_data)
    
    def load(self, filename):
        with open(filename, 'rb') as file:
            binary_data = file.read()
        
        offset = 0

        # 1. Load the amount of controlled inputs
        controlled_inputs = []
        controlled_inputs_len = int.from_bytes(binary_data[offset:offset + 1], 'big')
        offset += 1

        # 2. Load the controlled inputs
        for i in range(controlled_inputs_len):
            controlled_inputs.append(int.from_bytes(binary_data[offset:offset + 1], 'big'))
            offset += 1
        
        # 3. Load the amount of controlled dca
        controlled_dca = []
        controlled_dca_len = int.from_bytes(binary_data[offset:offset + 1], 'big')
        offset += 1

        # 4. Load the controlled dca
        for i in range(controlled_dca_len):
            controlled_dca.append(int.from_bytes(binary_data[offset:offset + 1], 'big'))
            offset += 1
        
        # 5. Load the amount of effect ports
        effect_ports = []
        effect_ports_len = int.from_bytes(binary_data[offset:offset + 1], 'big')
        offset += 1

        # 6. Load the effect ports
        for i in range(effect_ports_len):
            effect_ports.append(int.from_bytes(binary_data[offset:offset + 1], 'big'))
            offset += 1
        
        # 7. Load input alias
        input_alias = {}
        input_alias_len = int.from_bytes(binary_data[offset:offset + 1], 'big')
        offset += 1

        for i in range(input_alias_len):
            input = int.from_bytes(binary_data[offset:offset + 2], 'big')
            offset += 2
            alias_len = int.from_bytes(binary_data[offset:offset + 1], 'big')
            offset += 1
            alias = binary_data[offset:offset + alias_len].decode('utf-8')
            offset += alias_len
            input_alias[input] = alias
        
        # 8. Load the cue data
        cues = []
        cue_len = int.from_bytes(binary_data[offset:offset + 4], 'big')
        offset += 4
        for i in range(cue_len):
            cue = {}
            # 8.1 Load the cue number
            cue_number_len = int.from_bytes(binary_data[offset:offset + 2], 'big')
            offset += 2
            cue['number'] = binary_data[offset:offset + cue_number_len].decode('utf-8')
            offset += cue_number_len

            # 8.2 Load the cue name
            cue_name_len = int.from_bytes(binary_data[offset:offset + 2], 'big')
            offset += 2
            cue['name'] = binary_data[offset:offset + cue_name_len].decode('utf-8')
            offset += cue_name_len

            # 8.3 Load the dca assignments
            cue['dca'] = {}
            for dca in controlled_dca:
                cue['dca'][dca] = []
                dca_len = int.from_bytes(binary_data[offset:offset + 1], 'big')
                offset += 1
                for j in range(dca_len):
                    cue['dca'][dca].append(int.from_bytes(binary_data[offset:offset + 1], 'big'))
                    offset += 1
            
            # 8.4 Load the effect assignments
            cue['effects'] = {}
            for dca in controlled_dca:
                cue['effects'][dca] = []
                effect_len = int.from_bytes(binary_data[offset:offset + 1], 'big')
                offset += 1
                for j in range(effect_len):
                    cue['effects'][dca].append(int.from_bytes(binary_data[offset:offset + 1], 'big'))
                    offset += 1
            
            # 8.5 Load the dca names
            cue['dca_name'] = {}
            for dca in controlled_dca:
                dca_name_len = int.from_bytes(binary_data[offset:offset + 2], 'big')
                offset += 2
                cue['dca_name'][dca] = binary_data[offset:offset + dca_name_len].decode('utf-8')
                offset += dca_name_len
            
            cues.append(cue)
        
        mutex.acquire()
        self.controlled_inputs = controlled_inputs
        self.controlled_dca = controlled_dca
        self.effect_ports = effect_ports
        self.input_alias = input_alias
        self.cues = Mix_cue_sheet.from_array(controlled_inputs, controlled_dca, effect_ports, cues)
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

def generate_callback_function(nrpn_parser):
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

def generate_nrpn_parser(ls9_mix):
    def parse_nrpn_input(address, value):
        if address >= 0x3a5a and address <= 0x3a61:
            # Mute Master
            if address - 0x3a5a + 1 == button_next_cue:
                ls9_mix.next_cue()
            elif address - 0x3a5a + 1 == button_prev_cue:
                ls9_mix.previous_cue()
    return parse_nrpn_input

class LS9_mix_server():
    def __init__(self, controlled_inputs = controlled_inputs, controlled_dca = controlled_dca, effect_ports = effect_ports, input_alias = input_alias):
        self.midi_in = rtmidi.MidiIn()
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
        self.enabled = True     
        self.mix.connected = True     

        self.mix.send_initialize()

        self.midi_in.set_callback(generate_callback_function(generate_nrpn_parser(self.mix)))

        def socket_poll():
            while 1:
                data = self.osc_server.listen()
                
                # Truncate the message to the first 0
                data = data[:data.index(0)]
                print(data)
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