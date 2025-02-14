Because the LS9 console recieves and sends NRPN message, I can make use of this function to make a software like Theatermix based on MIXBUS instead of DCA.

A major difference of MIXBUS and DCA for me is the panning, cuz DCA will not affect the panning of the original channels while MIXBUS will always be mono. So if we use software to store and control the panning of MIXBUS' send to MATRIX, it will act the analogously to DCA faders in this way. Another fallback is that MIXBUS will not affect the effect send of its grouped channels. Because we will probably use only one Reverb send at a time in a musical, we could use MATRIX as its send target, and send from MIXBUS instead of element channels. Other special effects would just be inserted to individual channels.


SO my software needs to accomplish the following tasks to function fully,
1. Control the MUTE of each element channel
2. Control the SEND ON/OFF of each element channel
3. Control the PAN of element channel (for ensemble group), and MIXBUS send to MATRIX
4. Control the SEND ON/OF of each MIXBUS
5. Control INSTERT ON of each element channel

I intend to use MAXMSP to process the midi signal, and create a maybe usable GUI to program the show. Then, let MAXMSP to recieve OSC from QLab to trigger the GOs, so it will be less possible to mess up the MAX patch.