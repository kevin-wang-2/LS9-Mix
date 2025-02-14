#!/usr/bin/env python3

from time import sleep

import rtmidi

midi_out = rtmidi.MidiOut()
avaliable_ports = midi_out.get_ports()

print(avaliable_ports)
idx = input('Select MIDI device: ')
midi_out.open_port(int(idx))

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

class LS9_mix:
    def __init__(self, NRPN, controlled_inputs, controlled_dca, cues):
        self.NRPN = NRPN
        self.controlled_inputs = controlled_inputs
        self.controlled_dca = controlled_dca
        self.channel_on = {}
        for input in controlled_inputs:
            self.channel_on[input] = 0
        
        self.dca = {}
        for dca in controlled_dca:
            self.dca[dca] = []
        
        self.cues = cues
        self.current_cue = 0 # 0 is line-check

    def send_initialize(self):
        for input in self.controlled_inputs:
            for dca in self.controlled_dca:
                self.NRPN.send_input_to_mix_off(input, dca)
            self.NRPN.send_input_on(input)

    def go_cue(self, target_cue_idx):
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

ls9 = LS9_NRPN(midi_out, 0)
controlled_inputs = range(33, 49)
controlled_dca = range(1, 9)

mix = LS9_mix(ls9, controlled_inputs, controlled_dca, [
    {'number': '1', 'dca': {1: [33, 34], 2: [35, 36], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}},
    {'number': '2', 'dca': {1: [33], 2: [35], 3: [], 4: [], 5: [], 6: [], 7: [], 8: [41, 42, 43, 44, 45, 46, 47, 48]}},
    {'number': '3', 'dca': {1: [33], 2: [], 3: [], 4: [], 5: [], 6: [], 7: [], 8: []}},
])
mix.send_initialize()
input("")
mix.next_cue()
input("")
mix.next_cue()
input("")
mix.next_cue()
