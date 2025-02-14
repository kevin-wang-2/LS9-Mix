global controlledInputs
global DCAs
global lastDCA
global currentOns
global lastOns

set controlledInputs to {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}
set DCAs to {1, 2, 3, 4, 5, 6, 7, 8}
set lastDCA to {}

on createCC(channel_num, cc, value)
	tell application id "com.figure53.QLab.5"
		make front workspace type "MIDI"
		set newCue to last item of (selected of front workspace as list)
		
		-- Set MIDI cue properties
		set q number of newCue to ""
		set q name of newCue to "CC" & cc & ": " & value
		set midi patch number of newCue to 1
		set command of newCue to control_change
		set channel of newCue to channel_num
		set byte one of newCue to cc
		set byte two of newCue to value
		
		return newCue
	end tell
end createCC

on createNRPM(MSB, LSB, Value_MSB, Value_LSB)
	set LSB_Cue to createCC(1, 98, LSB)
	set MSB_Cue to createCC(1, 99, MSB)
	set Value_LSB_Cue to createCC(1, 6, Value_LSB)
	set Value_MSB_Cue to createCC(1, 38, Value_MSB)
	
	tell application id "com.figure53.QLab.5"
		
		set q name of MSB_Cue to "MSB"
		set q name of LSB_Cue to "LSB"
		set q name of Value_LSB_Cue to "Value LSB"
		set q name of Value_MSB_Cue to "Value MSB"
		
		make front workspace type "Group"
		set groupCue to last item of (selected of front workspace as list)
		move MSB_Cue to the end of groupCue
		move LSB_Cue to the end of groupCue
		move Value_LSB_Cue to the end of groupCue
		move Value_MSB_Cue to the end of groupCue
		
		return groupCue
	end tell
end createNRPM

on makeInputChannelOnCue(nrpm_channel)
	set base to nrpm_channel + 1461
	set MSB_channel to base div 128
	set LSB_channel to base mod 128
	
	set currentCue to createNRPM(MSB_channel, LSB_channel, 0, 64)
	
	tell application id "com.figure53.QLab.5"
		set q name of currentCue to "In" & nrpm_channel & " On"
	end tell

    return currentCue
end makeInputChannelOnCue

on makeInputChannelOffCue(nrpm_channel)
	set base to nrpm_channel + 1461
	set MSB_channel to base div 128
	set LSB_channel to base mod 128
	
	set currentCue to createNRPM(MSB_channel, LSB_channel, 0, 0)
	
	tell application id "com.figure53.QLab.5"
		set q name of currentCue to "In" & nrpm_channel & " Off"
	end tell

    return currentCue
end makeInputChannelOffCue

on makeInputChannelMixOnCue(nrpm_channel, mix)
    if nrpm_channel < 57 then
        set base to 11311
        set base to base + (mix - 1) * 64
        set base to base + nrpm_channel
    else
        set base to 4393
        set base to base + (mix - 1) * 8
        set base to base + nrpm_channel - 56
    end if
	set MSB_channel to base div 128
	set LSB_channel to base mod 128
	
	set currentCue to createNRPM(MSB_channel, LSB_channel, 0, 64)
	
	tell application id "com.figure53.QLab.5"
		set q name of currentCue to "In" & nrpm_channel & " Mix" & mix & " On"
	end tell
	
    return currentCue
end makeInputChannelMixOnCue

on makeInputChannelMixOffCue(nrpm_channel, mix)
    if nrpm_channel < 57 then
        set base to 11311
        set base to base + (mix - 1) * 64
        set base to base + nrpm_channel
    else
        set base to 4393
        set base to base + (mix - 1) * 8
        set base to base + nrpm_channel - 56
    end if
	set MSB_channel to base div 128
	set LSB_channel to base mod 128
	
	set currentCue to createNRPM(MSB_channel, LSB_channel, 0, 0)
	
	tell application id "com.figure53.QLab.5"
		set q name of currentCue to "In" & nrpm_channel & " Mix" & mix & " Off"
	end tell
	
    return currentCue
end makeInputChannelMixOffCue

on makeOutputChannelMatrixOnCue(nrpm_channel, matrix)
    set base to 2739
    set base to base + (matrix - 1) * 22
    set base to base + nrpm_channel
    set MSB_channel to base div 128
    set LSB_channel to base mod 128

    set currentCue to createNRPM(MSB_channel, LSB_channel, 0, 64)

    tell application id "com.figure53.QLab.5"
        set q name of currentCue to "Out" & nrpm_channel & " Matrix" & matrix & " On"
    end tell
	
    return currentCue
end makeOutputChannelMatrixOnCue

on makeOutputChannelMatrixOffCue(nrpm_channel, matrix)
    set base to 2739
    set base to base + (matrix - 1) * 22
    set base to base + nrpm_channel
    set MSB_channel to base div 128
    set LSB_channel to base mod 128

    set currentCue to createNRPM(MSB_channel, LSB_channel, 0, 0)

    tell application id "com.figure53.QLab.5"
        set q name of currentCue to "Out" & nrpm_channel & " Matrix" & matrix & " Off"
    end tell
	
    return currentCue
end makeOutputChannelMatrixOffCue

on createDCA(mix, inputList)
    -- loop through inputList and set Mix On for each of them
    tell application id "com.figure53.QLab.5"
        make front workspace type "Group"
        set groupCue to last item of (selected of front workspace as list)
        set q name of groupCue to "DCA" & mix
    end tell

    set lastCurrentDCA to item mix of lastDCA

    -- Set currentOns to 1 if the input is in the inputList
    if count of inputList is not 0 then
        repeat with i from 1 to count of inputList
            set currentInput to item i of inputList
            if currentInput is not in currentOns then
                set currentOns to currentOns & {currentInput}
            end if
        end repeat
    end if

    -- Remove all the previous inputs if they are not in the current input list
    if count of lastCurrentDCA is not 0 then
        repeat with i from 1 to count of lastCurrentDCA
            set currentInput to item i of lastCurrentDCA
            if currentInput is not in inputList then
                set currentCue to makeInputChannelMixOffCue(currentInput, mix)
                tell application id "com.figure53.QLab.5"
                    move currentCue to the end of groupCue
                end tell
            end if
        end repeat
    end

    -- Add all the new inputs if they are not in the last input list
    if count of inputList is not 0 then
        repeat with i from 1 to count of inputList
            set currentInput to item i of inputList
            if currentInput is not in lastCurrentDCA then
                set currentCue to makeInputChannelMixOnCue(currentInput, mix)
                tell application id "com.figure53.QLab.5"
                    move currentCue to the end of groupCue
                end tell
            end if
        end repeat
    end

    return groupCue
end

on generateCue(num, DCAList)

    tell application id "com.figure53.QLab.5"
        make front workspace type "Group"
        set groupCue to last item of (selected of front workspace as list)
        set q name of groupCue to "CUE" & num
    end tell

    -- Reset currentOns
    set currentOns to {}

    repeat with i from 1 to count of DCAs
        set currentDCAList to item i of DCAList
        set currentDCA to item i of DCAs
        set currentCue to createDCA(currentDCA, currentDCAList)

        tell application id "com.figure53.QLab.5"
            move currentCue to the end of groupCue
        end tell
    end repeat

    -- Turn on the inputs that are in currentOns but not in lastOns
    repeat with i from 1 to count of currentOns
        set currentInput to item i of currentOns
        if currentInput is not in lastOns then
            set currentCue to makeInputChannelOnCue(currentInput)
            tell application id "com.figure53.QLab.5"
                move currentCue to the end of groupCue
            end tell
        end if
    end repeat

    -- Turn off the inputs that are in lastOns but not in currentOns
    repeat with i from 1 to count of lastOns
        set currentInput to item i of lastOns
        if currentInput is not in currentOns then
            set currentCue to makeInputChannelOffCue(currentInput)
            tell application id "com.figure53.QLab.5"
                move currentCue to the end of groupCue
            end tell
        end if
    end repeat

    set lastDCA to DCAList
    set lastOns to currentOns
end generateCue

on initialize()
    tell application id "com.figure53.QLab.5"
        make front workspace type "Group"
        set groupCue to last item of (selected of front workspace as list)
        set q name of groupCue to "Line Check"
    end tell

    repeat with channel_idx from 1 to count of controlledInputs
        set currentInput to item channel_idx of controlledInputs
        repeat with dca_idx from 1 to count of DCAs
            set currentDCA to item dca_idx of DCAs
            set currentCue to makeInputChannelMixOffCue(currentInput, currentDCA)
            tell application id "com.figure53.QLab.5"
                move currentCue to the end of groupCue
            end tell
        end repeat

        set currentCue to makeInputChannelOnCue(currentInput)
        tell application id "com.figure53.QLab.5"
            move currentCue to the end of groupCue
        end tell
    end repeat

    -- Set lastOns to all 0s with the count of controlledInputs
    set lastOns to controlledInputs

    -- Set lastDCAs to all {}s with the count of DCAs
    repeat with i from 1 to count of DCAs
        set lastDCA to lastDCA & {{}}
    end repeat
end initialize

initialize()
generateCue(1, {{1}, {2}, {3}, {4}, {5}, {6}, {7, 8, 9, 10, 11}, {12, 13, 14, 15, 16}})
generateCue(2, {{2}, {3}, {}, {}, {}, {}, {}, {6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16}})
generateCue(3, {{}, {}, {}, {}, {}, {}, {}, {}})
generateCue(4, {{1}, {2}, {3}, {4}, {5}, {6}, {7, 8, 9, 10, 11}, {12, 13, 14, 15, 16}})
