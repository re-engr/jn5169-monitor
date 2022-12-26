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
#	
# **********************************************************************************
# Contact: re-engr.ru (https://github.com/re-engr/jn5169-monitor)
# Version: 
# 	- 0.3 (Dec 26 2022) 

import serial
import binascii
import time
import logging

logging.basicConfig(level=logging.INFO) #DEBUG INFO

ser = serial.Serial(
    port='COM4',\
    baudrate=38400,\
    parity=serial.PARITY_NONE,\
    stopbits=serial.STOPBITS_ONE,\
    bytesize=serial.EIGHTBITS,\
    timeout=None)

def cal_cs(dat, len):
  cs=0
  for i in range(len):
    cs ^= dat[i]           
  return cs

def mon_exit(rc): 
  if rc == 1:
      logging.info(" CS bad")
      
  logging.info("\n\nPress enter to exit") 
  ser.close()
  input()
  quit()
    
CMD_FLASH_PRG_REQ = 0x09
CMD_SECTOR_ERASE_REQ = 0x0D
CMD_SUCCESSFUL = 0x00

SECTOR_SIZE = 0x8000
LOWER_FLASH = 0 #num sector
UPPER_FLASH = 8
lower_upper = [LOWER_FLASH,UPPER_FLASH]
    
pattern=[[0x07, CMD_FLASH_PRG_REQ, 0x00, 0x00, 0x00, 0x00, 0xFF, 0x00], #FF - blank
         [0x07, CMD_FLASH_PRG_REQ, 0x00, 0x00, 0x00, 0x00, 0x12, 0x00], #12 34 56 78... MAGIC NUMBER
         [0x07, CMD_FLASH_PRG_REQ, 0x21, 0x00, 0x00, 0x00, 0x03, 0x00], #0x20 - 0x23 32-bit Length of Binary Image in bytes; 0x21
         [0x07, CMD_FLASH_PRG_REQ, 0x21, 0x00, 0x00, 0x00, 0x02, 0x00]]
found = 0
test_size = 0
sector_for_write_copy = LOWER_FLASH
sector_for_write = LOWER_FLASH
sector_curr_fw = LOWER_FLASH
#------------------------------------------------
logging.info("Scanning flash:")
for j in range(4): 
    if j==2  and test_size==0:
        break
        
    for sector_for_write in lower_upper:  
        if test_size == 1:
            sector_for_write = sector_for_write_copy
            
        check_cmd = bytearray(pattern[j])  
        check_cmd[4] = (sector_for_write*SECTOR_SIZE)>>16 #num sector -> addr
        
        for i in range(0,7):
            check_cmd[7] ^= check_cmd[i]    
            
        logging.debug([hex(x) for x in check_cmd])
        ser.write(check_cmd)
        ret = ser.read(4)
        logging.debug([hex(x) for x in ret])
        if cal_cs(ret,4):
          mon_exit(1)
            
        if ret[2] == CMD_SUCCESSFUL:    #ok
        
            if j == 0:
                sector_curr_fw = sector_for_write ^ UPPER_FLASH #4 * 0x10000 = half flash
                found = 1
            elif j == 1:   
                test_size = 1
                sector_for_write_copy = sector_for_write
                break
            elif j == 2:  
                sector_curr_fw = sector_for_write
                sector_for_write ^= UPPER_FLASH
                found = 1
            else: #3
                sector_curr_fw = sector_for_write
                sector_for_write ^= UPPER_FLASH
                found = 1                
            
            if found == 1:                
                break 
                
        if test_size == 1:
            break
            
    if found:
        break

if test_size == 1:
    sector_curr_fw = sector_for_write ^ UPPER_FLASH #4 * 0x10000 = half flash
    found = 1
  
if found == 0:   
    logging.info(" Writable sector not found")
    mon_exit(0)   
    
logging.info(" Sector with firmware: %d",sector_curr_fw)
logging.info(" Sector for monitor writing: %d",sector_for_write)
#------------------------------------------------
logging.info("Sector erase: %d",sector_for_write)
erase_sector = bytearray([0x03, CMD_SECTOR_ERASE_REQ, sector_for_write, 0x00])
for i in range(0,3):
  erase_sector[3] ^= erase_sector[i]
logging.debug([hex(x) for x in erase_sector])
ser.write(erase_sector)
ret = ser.read(4)
logging.debug([hex(x) for x in ret])
if cal_cs(ret,4):
  mon_exit(1)
#------------------------------------------------
logging.info("Write firmware monitor: %d", sector_for_write)
addr = 0
with open("mon5169.bin", "rb") as f:
    bytes = bytearray(f.read(4))    #skip file version 0F 03 00 0B and 12     
    bytes = bytearray(f.read(128))
    bytes[0] = 0xFF            #12 mag
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
        if cal_cs(ret,4):
            f.close()
            mon_exit(1)
        #logging.debug([hex(x) for x in ret])        
        if ret[2] != CMD_SUCCESSFUL:    #error
            logging.info(" Flashing error")
            break
        logging.info(" 0x%04x OK", addr)    
        addr += 128				
        bytes = list(f.read(128))            
    else:              
        #------------------------------------------------
        logging.info("Write MAGIC_NUMBER 12 for monitor: %d",sector_for_write)
        write_magic_number = bytearray([0x07, CMD_FLASH_PRG_REQ, 0x00, 0x00, 0x00, 0x00, 0x12, 0x00])
        write_magic_number[4] = (sector_for_write*SECTOR_SIZE)>>16 
        for i in range(0,7):
          write_magic_number[7] ^= write_magic_number[i]
        logging.debug([hex(x) for x in write_magic_number])
        ser.write(write_magic_number)
        ret = ser.read(4)
        if cal_cs(ret,4):
            f.close()
            mon_exit(1)
        logging.debug([hex(x) for x in ret])
        
        logging.info("Invalidate MAGIC_NUMBER for firmware: %d",sector_curr_fw)
        erase_magic_number = bytearray([0x07, CMD_FLASH_PRG_REQ, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
        erase_magic_number[4] = (sector_curr_fw*SECTOR_SIZE)>>16 
        for i in range(0,7):
          erase_magic_number[7] ^= erase_magic_number[i]
        logging.debug([hex(x) for x in erase_magic_number])
        ser.write(erase_magic_number)
        ret = ser.read(4)
        if cal_cs(ret,4):
            f.close()            
        logging.debug([hex(x) for x in ret])
     
    f.close()
    logging.info("Completed")         
    mon_exit(0)


