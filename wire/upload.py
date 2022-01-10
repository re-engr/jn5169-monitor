# Script for writing to the JN5169 monitor program 
# **********************************************************************************
# These actions may damage the device! 
# If the device has an OTA update, then you need to find out in which 
#	part of the flash memory the firmware is located
#
# 1. Enter in bootloader;
# 2. Set the serial port number;
# 3. Run this script;
# 4. If successful, you will see return codes [0x3, 0x0a, 0x0, 0x9].
# 5. Start the terminal and set the same port number, baud rate 115200 8n1;
# 6. Remove the jumper from the bootloader contact and restart the microcontroller;
# 7. If everything is in order, you will see a message in the terminal prompting what to do next;
# 8. Before pressing the key, enable output logging;
# 9. 'f' - you will have all the memory 0x00080000 - 0x000FFFFF (Flash Applications Code (512 kB))
# 	 'w' - the program will send the firmware file, with the correct MAGIC_NUMBER and file ID (0f 03 00 0b)
# 10. Well done! Now you can flash this file back and restore your device :)
#	
# **********************************************************************************
# Contact: re-engr.ru (https://github.com/re-engr/jn5169-monitor)
# Version: 
# 	- 0.1 (Jan 10 2022) 

import serial
import binascii

SECTOR_FOR_WRITE = 0x04 #If the answer is [0x3, 0x0a, 0xfe, 0xf7], set 0x5, 0x6 or 0x7. 
                        #Most likely the memory sector is not cleared

ser = serial.Serial(
    port='COM5',\
    baudrate=38400,\
    parity=serial.PARITY_NONE,\
    stopbits=serial.STOPBITS_ONE,\
    bytesize=serial.EIGHTBITS,\
    timeout=None)

print ("Invalidate MAGIC_NUMBER")
erase_magic_number = bytearray([0x07, 0x09, 0x00, 0x00, 0x00, 0x00, 0x00, 0x0E])
ser.write(erase_magic_number)
ret = ser.read(4)
print([hex(x) for x in ret])

print ("Write firmware")
addr = 0
with open("mon5169.bin", "rb") as f:
	bytes = bytearray(f.read(128))
	while len(bytes) > 0:
		Message = bytearray([len(bytes) + 6, 0x09, 0x00, 0x00, SECTOR_FOR_WRITE, 0x00])	
		Message[2] = (addr&0xFF)
		Message[3] = ((addr>>8)&0xFF)
		Message.extend(bytes)
		
		cs = bytearray([0])
		for i in range(0,len(bytes)+6):
			cs[0] = cs[0] ^ Message[i]
		
		Message.extend(cs)
		ser.write(Message)
		ret = ser.read(4)
		print([hex(x) for x in ret])
		
		addr += 128				
		bytes = list(f.read(128))
		
	f.close()
	ser.close()
	
	input("Flashing completed\n\nPress any key to exit")
	