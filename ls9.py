#!/usr/bin/env python3

from time import sleep

import rtmidi
import socket

midi_out = rtmidi.MidiOut()
avaliable_ports = midi_out.get_ports()

effect_ports = (7, 8)

# print(avaliable_ports)
# idx = input('Select MIDI device: ')
# midi_out.open_port(int(idx))

# Get the first port with 'USB Midi' in the name
for i, port in enumerate(avaliable_ports):
    if 'USB Midi' in port:
        midi_out.open_port(i)
        break

class LS9_NRPN:
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
    def __init__(self, NRPN, controlled_inputs, controlled_dca, cues):
        self.NRPN = NRPN
        self.controlled_inputs = controlled_inputs
        self.controlled_dca = controlled_dca
        
        self.cues = cues
        self.current_cue = 0 # 0 is line-check

    def send_initialize(self):
        for input in self.controlled_inputs:
            for dca in self.controlled_dca:
                self.NRPN.send_input_to_mix_off(input, dca)
            self.NRPN.send_input_on(input)
        
        for dca in self.controlled_dca:
            for effect in effect_ports:
                self.NRPN.send_output_to_matrix_off(dca, effect)
        self.channel_on = {}
        for input in self.controlled_inputs:
            self.channel_on[input] = 0
        
        self.dca = {}
        self.effects = {}
        for dca in self.controlled_dca:
            self.dca[dca] = []
            self.effects[dca] = []

    def go_cue(self, target_cue_idx):
        if target_cue_idx == -1:
            self.send_initialize()
            self.current_cue = 0
            return
        if target_cue_idx >= len(self.cues) or target_cue_idx < -1:
            return
        target_cue = self.cues[target_cue_idx]['dca']
        channel_on = {}
        for dca in self.controlled_dca:
            current_assignment = target_cue[dca]
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
                if effect not in self.cues[target_cue_idx]['effects'][dca]:
                    self.NRPN.send_output_to_matrix_off(dca, effect)
            for effect in self.cues[target_cue_idx]['effects'][dca]:
                if effect not in self.effects[dca]:
                    self.NRPN.send_output_to_matrix_on(dca, effect)
            self.effects[dca] = self.cues[target_cue_idx]['effects'][dca]
        for input in self.controlled_inputs:
            if input in channel_on and input not in self.channel_on:
                self.NRPN.send_input_on(input)
            if input in self.channel_on and input not in channel_on:
                self.NRPN.send_input_off(input)
        self.channel_on = channel_on

    def next_cue(self):
        self.go_cue(self.current_cue)
        self.current_cue += 1
    
    def previous_cue(self):
        if self.current_cue == 0:
            return
        if self.current_cue == 1:
            self.send_initialize()
            self.current_cue = 0
            return
        self.go_cue(self.current_cue)
        self.current_cue -= 1

class OSC_server():
    def __init__(self, port):
        # Establish UDP Socket server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(('localhost', port))
        self.sock.settimeout(0.1)
    
    def listen(self):
        try:
            data, addr = self.sock.recvfrom(1024)
            return data
        except socket.timeout:
            return None

ls9 = LS9_NRPN(midi_out, 0)
controlled_inputs = range(33, 49)
controlled_dca = range(1, 9)

mix = LS9_mix(ls9, controlled_inputs, controlled_dca, [
    {'number': '1', 'dca': {1: [33, 34], 2: [35, 36], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}, 'effects': {1: [], 2: [7], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}},
    {'number': '2', 'dca': {1: [33], 2: [35], 3: [], 4: [], 5: [], 6: [], 7: [], 8: [41, 42, 43, 44, 45, 46, 47, 48]}, 'effects': {1: [7], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}},
    {'number': '3', 'dca': {1: [33], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}, 'effects': {1: [], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}},
    {'number': '4', 'dca': {1: [38], 2: [47, 41], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}, 'effects': {1: [8], 2: [7], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}},
])
osc = OSC_server(53001)

mix.send_initialize()

while 1:
    data = osc.listen()
    if data is None:
        continue
    

    # Truncate the message to the first 0
    data = data[:data.index(0)]
    print(data)
    if data == b'/next':
        mix.next_cue()
    elif data == b'/prev':
        mix.previous_cue()

    # Process go cues
    if data[:4] == b'/go/':
        cue = int(data[4:])
        mix.go_cue(cue - 1)
