# Script for writing to the JN5169 monitor program 
# **********************************************************************************
# These actions may damage the device! 
#
# 1. Enter in bootloader;
# 2. Set the serial port number;
# 3. Run this script;
# 4. If successful, you will see Flashing comlited.
# 5. Start the terminal and set the same port number, baud rate 115200 8n1;
# 6. Remove the jumper from the bootloader contact and restart the microcontroller;
# 7. If everything is in order, you will see a message in the terminal prompting what to do next;
# 8. Before pressing the key, enable output logging;
# 9. 'f' - you will have all the memory 0x00080000 - 0x000FFFFF (Flash Applications Code (512 kB))
# 	 'w' - the program will send the firmware file, with the correct MAGIC_NUMBER and file ID (0f 03 00 0b)
#	
# **********************************************************************************
# Contact: re-engr.ru (https://github.com/re-engr/jn5169-monitor)
# Version: 
# 	- 0.2 (May 9 2022) 

import serial
import binascii
import time
import logging

logging.basicConfig(level=logging.INFO) #DEBUG

ser = serial.Serial(
    port='COM5',\
    baudrate=38400,\
    parity=serial.PARITY_NONE,\
    stopbits=serial.STOPBITS_ONE,\
    bytesize=serial.EIGHTBITS,\
    timeout=None)

CMD_FLASH_PRG_REQ = 0x09
CMD_SECTOR_ERASE_REQ = 0x0D
CMD_SUCCESSFUL = 0x00

SECTOR_SIZE = 0x8000
LOWER_FLASH = 0 #num sector
UPPER_FLASH = 8
lower_upper = [LOWER_FLASH,UPPER_FLASH]
    
pattern=[[0x07, CMD_FLASH_PRG_REQ, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00], #FF - blank
         [0x07, CMD_FLASH_PRG_REQ, 0x00, 0x00, 0x00, 0x00, 0x12, 0x00]] #12 34 56 78... MAGIC NUMBER
found = 0
#------------------------------------------------
for j in range(2): 
    for sector_for_write in lower_upper:  
        check_cmd = bytearray(pattern[j])  
        check_cmd[4] = (sector_for_write*SECTOR_SIZE)>>16 #num sector -> addr
        
        for i in range(0,7):
            check_cmd[7] ^= check_cmd[i]    
            
        logging.debug([hex(x) for x in check_cmd])
        ser.write(check_cmd)
        ret = ser.read(4)
        logging.debug([hex(x) for x in ret])
        if ret[2] == CMD_SUCCESSFUL:    #ok
            
            if j == 0:
                sector_curr_fw = sector_for_write ^ UPPER_FLASH #4 * 0x10000 = half flash
            else:
                sector_curr_fw = sector_for_write
                sector_for_write ^= UPPER_FLASH
            found = 1
            logging.info("Sector for writing: %d",sector_for_write)
            break  
    if found:
        break
else:    
    ser.close()	
    logging.info("Writable sector not found\n\nPress any key to exit")
    input()
    quit()    
#------------------------------------------------
logging.info("Invalidate MAGIC_NUMBER: %d",sector_curr_fw)
erase_magic_number = bytearray([0x07, CMD_FLASH_PRG_REQ, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
erase_magic_number[4] = (sector_curr_fw*SECTOR_SIZE)>>16 
for i in range(0,7):
	erase_magic_number[7] ^= erase_magic_number[i]
logging.debug([hex(x) for x in erase_magic_number])
ser.write(erase_magic_number)
ret = ser.read(4)
logging.debug([hex(x) for x in ret])
#------------------------------------------------
logging.info("Sector erase: %d",sector_for_write)
erase_sector = bytearray([0x03, CMD_SECTOR_ERASE_REQ, sector_for_write, 0x00])
for i in range(0,3):
	erase_sector[3] ^= erase_sector[i]
logging.debug([hex(x) for x in erase_sector])
ser.write(erase_sector)
ret = ser.read(4)
logging.debug([hex(x) for x in ret])
#------------------------------------------------
logging.info("Write firmware: %d", sector_for_write)
addr = 0
with open("mon5169.bin", "rb") as f:
    bytes = bytearray(f.read(4))    #skip file version 0F 03 00 0B
    bytes = bytearray(f.read(128))
    while len(bytes) > 0:
        Message = bytearray([len(bytes) + 6, CMD_FLASH_PRG_REQ, 0x00, 0x00, 0x00, 0x00])
        Message[4] = (sector_for_write*SECTOR_SIZE)>>16
        Message[2] = (addr&0xFF)
        Message[3] = ((addr>>8)&0xFF)
        Message.extend(bytes)

        cs = bytearray([0])
        for i in range(0,len(bytes)+6):
            cs[0] ^= Message[i]

        Message.extend(cs)
        ser.write(Message)
        ret = ser.read(4)
        #logging.debug([hex(x) for x in ret])        
        if ret[2] != CMD_SUCCESSFUL:    #error
            logging.info(" Flashing error")
            break
        logging.info(" 0x%04x OK", addr)    
        addr += 128				
        bytes = list(f.read(128))            
    else:
        logging.info("Flashing completed")
        
    f.close()
    ser.close()

    logging.info("\n\nPress any key to exit")
    input()
