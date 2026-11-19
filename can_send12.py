# coding: utf-8

## pip3 install udsoncan
## pip3 install can-isotp

# pip3 install python-can
# pip3 install pyaes

# (C) Dennis Noermann 2018-2023
# This is free for all
# You are free to support me via Paypal dennis.noermann@noernet.de
#
# This is my Implementation of following VW used CAN Protocolls
# Mainly used for Debugging Cluster ACC and ABS of VW PQ25 and PQ35 cars via CAN
# Its badly written and not Documented
# But it works for me :)
# Protocols implemented:
# - UDS
# - TP 2.0 & KWP2000 


################################################################################
# 31.08.2023 Initial git commit
#
################################################################################

# Interesting Commands for Cluster:
#  Engeneering AES KEY needed for all Cluster regarding Commands !!! 
# -TachoDumpEeprom
# -TachoDumpFlash
# -TachoDumpCpKeyRAM
# -TachoDumpRam
# -ReadEepromData
# -ReadInfo
# -TachoShowRam
# -WriteCPdata

# Interesting Commands for ACC:
# -WriteCPdata
# -3QFSwap

# Interesting Commands for ABS:
# -TP20_StartDiagnosticSession
# -TP20_SecurityAccess

from __future__ import print_function

import can
import binascii
import pyaes
import codecs
from datetime import datetime
import sys
from time import sleep
import numpy as np

global TP20Counter
TP20Counter = 0

boolQuiet = False

SendSeedRequest = [0x03,0x23,0x5A,0x3F,0x3A,0xA1,0xBD,0x01,0xEE,0xBB,0x32,0xF7,0xC9,0x88,0xB4,0xAC,0x2E,0x65,0x2F,0xB1,0xDE,0x2A,0x2B,0xFF,0xFF,0x07]

# keyhex, the AES Key for Cluster is included from external File Cluster_Aes_Keys.py
from Cluster_Aes_Keys import keyhex

key = codecs.decode(keyhex, 'hex')

def SplitToBytes(integer):
    return divmod(integer, 0x100)

def FillUpCanFrame(WorkingFrame):
    DataToFill = 8 - len(WorkingFrame)
    while DataToFill > 0: # Fill up to Full 8 Byte Can Frame with 0xAA
       DataToFill = DataToFill - 1
       WorkingFrame = WorkingFrame + [0xAA]
    return WorkingFrame

def UDS_Boot_ExitBl(bus,CanID):
        WorkingFrame = [0x55,0xAA,0x01,0x0C,0x11,0x22,0x33,0x03]
        
        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)
        recv_message = bus.recv(2.0) # 2 s Timeout   

# geht so nicht
def TachoReset(bus,CanID):
        msg = can.Message(arbitration_id=CanID,data=[0x02, 0x10, 0x60, 0xAA, 0xAA, 0xAA,0xAA,0xAA],is_extended_id=False)
        bus.send(msg)
        recv_message = bus.recv(2.0) # 2 s Timeout
        print (recv_message)    


def TachoReset2020(bus: can.bus.BusABC, CanID: int):
        msg = can.Message(arbitration_id=CanID,data=[0x02, 0x10, 0x60, 0xAA, 0xAA, 0xAA,0xAA,0xAA],is_extended_id=False)
        bus.send(msg)
        recv_message = UDS_Receive(bus, CanID)

        msg = can.Message(arbitration_id=CanID,data=[0x04, 0x2e, 0xfd, 0x00, 0x01, 0xAA,0xAA,0xAA],is_extended_id=False)
        bus.send(msg)        
        recv_message = bus.recv(2.0) # 2s Timeout

def UDS_ReceiveDecodeAndRemovePadding(SeedVomTacho):
        CountFrames=int(len(SeedVomTacho)/8)
        CountFrameTmp=CountFrames
        #print ("Frames: " + str(CountFrames))

        while CountFrames > 1: # Erste Byte der Frames x bis 2 löschen
         ByteToDel=((CountFrames-1)*8)
         #print("Byte Del Nr: " + str(ByteToDel))
         del SeedVomTacho[ByteToDel]
         CountFrames = CountFrames -1

        if CountFrameTmp == 1:
         UDSSize = SeedVomTacho[0]
         del SeedVomTacho[0:2] # die ersten 2 Bytes des ersten Frames löschen
        else:
         UDSSize = SeedVomTacho[1]
         del SeedVomTacho[0:3] # die ersten 3 Bytes des ersten Frames löschen

        return SeedVomTacho[0:UDSSize-1]

#def UDS_DiagnosticSessionControl(bus,CanID):
#        WorkingFrame = [0x02,0x10,0x03]
#        WorkingFrame = FillUpCanFrame(WorkingFrame)
#        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
#        bus.send(msg)
#        recv_message = bus.recv(2.0) # 2 s Timeout
#        print (recv_message.data)        


def UDS_DiagnosticSessionControl(bus: can.bus.BusABC, CanID: int, diagnosticSessionType: int):
        # 0x01 Default Session
        # 0x02 Programming session
        # 0x03 Extended diagnostic session
        # 0x60 ???
        WorkingFrame = [0x02,0x10,diagnosticSessionType]
        WorkingFrame = FillUpCanFrame(WorkingFrame)
        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)        
        print (str( codecs.encode( bytearray(UDS_Receive(bus,CanID)) ,'hex')) )
            
        #for receive_counter in range (0,10): # 10 frames empfangen
        #    recv_message = bus.recv(0.01) # 0.2 s Timeout
        #    if recv_message != None:
        #        if recv_message.data[1] == 0x7F and recv_message.data[2] == 0x10:
        #            #print("ID 0x%3.3x " % (CanID),end='')
        #            print ("error: diagnosticSessionType: 0x%x " % (diagnosticSessionType),end='')
        #            print (str( codecs.encode( bytearray(recv_message.data) ,'hex')) ) 
        #            break    


def UDS_RoutineControl(bus: can.bus.BusABC, CanID: int):
        # 0x01 Default Session
        # 0x02 Programming session
        # 0x03 Extended diagnostic session
        # 0x60 ???
        WorkingFrame = [0x04,0x31,0x01,0x02,0x03]
        WorkingFrame = FillUpCanFrame(WorkingFrame)
        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)        
        for receive_counter in range (0,10): # 10 frames empfangen
            recv_message = bus.recv(0.01) # 0.2 s Timeout
            if recv_message != None:
                if recv_message.data[1] == 0x7F and recv_message.data[2] == 0x10:
                    #print("ID 0x%3.3x " % (CanID),end='')
                    print("error")
                    print (str( codecs.encode( bytearray(recv_message.data) ,'hex')) ) 
                    break    

def BL_Seed(SeedVal):
        SeedVal = np.uint32(SeedVal) << 1
        #print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
        if SeedVal > 0xFFFFFFFF:
            print("SeedVal > 0xFFFFFFFF @ Start")
            for i in range(0,0x12):
                SeedVal = np.uint32(SeedVal) << 1
                if SeedVal > 0xFFFFFFFF:
                    SeedVal = SeedVal ^ 0x2FB67A9C
                    SeedVal = np.uint32(SeedVal) << 1
                    SeedVal = np.uint32(SeedVal)
                    SeedVal = SeedVal - 0x35658453
                    if SeedVal > 0xFFFFFFFF:
                        SeedVal = SeedVal ^ 0x20142BCD
                        SeedVal = SeedVal + 0x0BFB83250
                else:
                    SeedVal = SeedVal ^ 0x20142BCD
                    SeedVal = SeedVal + 0x0BFB83250                            
        
        else:
        
            for i in range(0,0xB):
                SeedVal = np.uint32(SeedVal)
                SeedVal = SeedVal + 0x0DAE7823C
                #print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
                if SeedVal > 0xFFFFFFFF:
                    SeedVal = SeedVal ^ 0x3DCEE873
                    #print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
                    SeedVal = np.uint32(SeedVal)
                    SeedVal = SeedVal + 0x48904532
                    #print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
                    if SeedVal > 0xFFFFFFFF:
                          SeedVal = SeedVal << 1
                          SeedVal = SeedVal ^ 0x0D68A42B
                          SeedVal = SeedVal << 1
        
        #print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
        SeedVal = np.uint32(SeedVal) << 1
        SeedVal = SeedVal + 1   # macht keinen sinn, ist aber so
        #SeedVal = np.uint32(SeedVal)
        #print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
        SeedVal = np.uint32(SeedVal) ^ 0x0A16532CD
        SeedVal = np.uint32(SeedVal)
        #print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))  
        
        return SeedVal


def UDS_SecurityAccess(bus,CanID,Magic):
 print("UDS_SecurityAccess " + str(hex(Magic)),end='')
 WorkingFrame = [0x02,0x27,0x03]
 WorkingFrame = FillUpCanFrame(WorkingFrame)
 msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
 bus.send(msg)          
 for receive_counter in range (0,10): # 10 frames empfangen
  recv_message = bus.recv(1) # 1 s Timeout
  if recv_message != None:
   if recv_message.data[0] == 0x06 and recv_message.data[1] == 0x67 and recv_message.data[2] == 0x03:
    #print (str( codecs.encode( bytearray(recv_message.data) ,'hex')) )
    break
  else: # timeout
   print("timeout")
   sys.exit(0)
 
 SeedVal32 = int.from_bytes(bytearray(recv_message.data)[3:7], byteorder='big', signed=False)
 print(" ... got Seed: " + str(hex(SeedVal32)),end='')

 SeedAnswer32 = SeedVal32 + Magic

 print(" ... Answer: " + str(hex(SeedAnswer32)),end='')

 SeedValAnswerByteArr =  int(SeedAnswer32).to_bytes(4, byteorder='big') 
 WorkingFrame = [0x06,0x27,0x04] + list(SeedValAnswerByteArr)
 WorkingFrame = FillUpCanFrame(WorkingFrame)
 msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
 bus.send(msg)          
 for receive_counter in range (0,10): # 10 frames empfangen
    recv_message = bus.recv(1) # 1 s Timeout
    if recv_message != None:
       if recv_message.data[0] == 0x03 and recv_message.data[1] == 0x7F:
        print ("Security Access Error")
        #print (str( codecs.encode( bytearray(recv_message.data) ,'hex')) )
        break
       if recv_message.data[0] == 0x02 and recv_message.data[1] == 0x67 and recv_message.data[2] == 0x04:
         print (" ... Security Access OK")
         return
 print("\n\nNot OK :( Exit \n\n")
 sys.exit(0)


def UDS_SecurityAccess_SA2(bus: can.bus.BusABC, CanID: int):
        SA2_ARRAY = [
                    ['814a246807814a0d87371ab7aa8184a2a371e84a0a879567b455931a38d24749932849ac5d4a1e681293057cd35e4a0d939135faac8703f941784a0781879ade3580814981877d9ab4674c' , '',''],
                    ['814a24680d814a0d8753040384818476cd4b4e4a0a874973b5f193bd4ebe4d4993d39e4afb4a1e681193b05da7404a0d93a47d9fab87534586ea4a07818740a3111f8149818735db54ec4c' , '5K0920863','0725'],
                    ['814a24680d814a0d87653040388184f76cd4b44a0a8724973b5f93ebd4ebe44993cd39e4af4a1e6811931b05da744a0d93ca47d9fa87b534586e4a078187040a311181498187d35db54e4c' , '',''],
                    ['814a24680d814a0d879653040381845f76cd4b4a0a87024973b5935ebd4ebe49930cd39e4a4a1e68119351b05da74a0d87fb53458693bca47d9f4a0781872040a31181498187fd35db544c' , '',''],
                    ['814a24680f814a0d87063bc8068184a2a371e84a0a878f44926c931a38d24749932849ac5d4a1e68089303f6459a4a0d939135faac8703f941784a07818757ad9e238149818736e40b3c4c' , '',''],
                    ['814a246812814a0d872fb67a9c8184356584534a0a8720142bcd93bfb83250499353acefd24a1e680b93dae7823c4a0d873dcee87393489045324a0781870d68a42b81498187a16532cd4c' , '7E0920970S', 'SW1104'],
                    ['814a246812814a0d87fb67a9c18184565845324a0a870142bcd193fb83250a49933acefd244a1e680b93ae7823cc4a0d938904532287dcee87324a078187d68a42bf8149818716532cd94c' , '','' ],
                    ['814a246817814a0d87a312d9e9819339c72acf4a0a87ed9b72a784fad16b7a49932c88d9c84a1e680a93a2acad914a0d841d0796ef87c1a2f9e44a07818730a83c2e81498187bec2dee54c' , '7E0920880J', 'SW0509'],
                    ['814a246817814a0d87a8312d9e81933e9c72ac4a0a87e6d9b72a84f9ad16b7499327c88d9c4a1e680a93a02acad94a0d841ed0796e87c31a2f9e4a0781873d0a83c281498187b4ec2dee4c' , '',''],
                    ['814a246817814a0d87aa312d9e8193039c72ac4a0a878ed9b72a84bfad16b749932c88d9c84a1e680a932a2acad94a0d875c1a2f9e8401d0796e4a078187f30a83c2814981876bec2dee4c' , '7E0920880S 7E0920882A 5N0920883F 5N0920883H 1K8920885L 7N0920880N 7N5920880J','SW1008 SW1018 SW1104 SW1109 SW2030 SW4030'],                                    
                    ]
        
        print("SA2 Array Key Count: %d"%(len(SA2_ARRAY)))

        SA2_Key_Counter=0
        while SA2_Key_Counter<len(SA2_ARRAY):
            SA2_HEX = SA2_ARRAY[SA2_Key_Counter][0]
            print("\nUsing SA2 Key[%d %s %s]: %s" % (SA2_Key_Counter, SA2_ARRAY[SA2_Key_Counter][1], SA2_ARRAY[SA2_Key_Counter][2], SA2_HEX))
            SA2_Key_Counter=SA2_Key_Counter+1
            SA2 = codecs.decode(SA2_HEX, 'hex')           
    
            WorkingFrame = [0x02,0x27,0x11]
            WorkingFrame = FillUpCanFrame(WorkingFrame)
            msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
            bus.send(msg)        
            for receive_counter in range (0,10): # 10 frames empfangen
                recv_message = bus.recv(0.01) # 0.2 s Timeout
                if recv_message != None:
                    if recv_message.data[0] == 0x02 and recv_message.data[1] == 0x7E:
                        #print("ID 0x%3.3x " % (CanID),end='')
                        print (recv_message)
                        print (str( codecs.encode( bytearray(recv_message.data) ,'hex')) )
                        break
                    print (str( codecs.encode( bytearray(recv_message.data) ,'hex')) )
                    SeedVal64 = int.from_bytes(bytearray(recv_message.data)[3:7], byteorder='big', signed=False)
                    
            SeedVal = np.int32(SeedVal64)
            print ("SeedVal: 0x%x " % (SeedVal),end="")

            SeedValAnswer = Tacho_SA2_Seed_Calc(SeedVal,SA2)      
            print("SeedValAnswer: 0x%x " % (SeedValAnswer))
    
            SeedValAnswerByteArr =  int(SeedValAnswer).to_bytes(4, byteorder='big') 
  
            WorkingFrame = [0x06,0x27,0x12] + list(SeedValAnswerByteArr)
            WorkingFrame = FillUpCanFrame(WorkingFrame)
            msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
            bus.send(msg)          
            for receive_counter in range (0,10): # 10 frames empfangen
                recv_message = bus.recv(0.01) # 0.2 s Timeout
                if recv_message != None:
                    if recv_message.data[0] == 0x03 and recv_message.data[1] == 0x7F:
                        #print ("Bl Seed Security Access Error")
                        #print (str( codecs.encode( bytearray(recv_message.data) ,'hex')) )
                        break
                    if recv_message.data[0] == 0x02 and recv_message.data[1] == 0x67 and recv_message.data[2] == 0x12:
                        print ("Bl Seed Security Access OK")
                        return
                        #break
        print("\n\nNo SA2 Key matched :( Exit \n\n")
        sys.exit(1)

def Tacho_SA2_Seed_Calc(SeedVal,SA2,Debug=False):
    # 2021.05.08 Implemented from Bootloader Dissassembly, thanks to daku for his input
    r10 = 0
    r25 = 0
    r26 = 0
    r27 = 0
    r28 = SeedVal
    PC = 0
    
    if Debug: print ("SeedVal: 0x%8.8x"%(r28))    
     
    while PC < len(SA2):
        if SA2[PC] == 0x81:
            if Debug: print ("SA2: PC=0x%2.2x Command: RSL (0x%2.2x)"%(PC,SA2[PC]))
            r27 = r28
            r27 = np.uint32(r27>>0x1F)
            r28 = np.uint32(r28<<0x01)
            if r27!=0:
                r28=r28|1
            
            PC=PC+1
            if Debug: print ("                                         r28: 0x%8.8x r27: 0x%8.8x r26: 0x%8.8x r25: 0x%8.8x r10: 0x%8.8x PC: 0x%8.8x"%(r28,r27,r26,r25,r10,PC))            
            
        elif SA2[PC] == 0x82:
            print ("TEST missing !!!")
            print ("SA2: PC=0x%2.2x Command: RSR (0x%2.2x)"%(PC,SA2[PC]))
            r27=r28+1
            r28 = np.uint32(r28>>0x01)            
            if r27!=0:
                r28=r28|0x80000000            
            PC=PC+1
        
        elif SA2[PC] == 0x84:
            if Debug: print ("SA2: PC=0x%2.2x Command: SUB (0x%2.2x)"%(PC,SA2[PC]))
            r10 = np.uint32( ((np.uint32(SA2[PC+1]))<<24) + (np.uint32((SA2[PC+2]))<<16) + (np.uint32((SA2[PC+3]))<<8) + (np.uint32((SA2[PC+4]))<<0) )
            
            if r10 < r28:
                r27 = 0
            else:
                r27 = 1
            
            r28 = np.uint32(r28 - r10)              
            
            PC=PC+5
            if Debug: print ("                                         r28: 0x%8.8x r27: 0x%8.8x r26: 0x%8.8x r25: 0x%8.8x r10: 0x%8.8x PC: 0x%8.8x"%(r28,r27,r26,r25,r10,PC))     
            

        elif SA2[PC] == 0x87:
            if Debug: print ("SA2: PC=0x%2.2x Command: XOR (0x%2.2x)"%(PC,SA2[PC]))
            r10 = np.uint32( ((np.uint32(SA2[PC+1]))<<24) + (np.uint32((SA2[PC+2]))<<16) + (np.uint32((SA2[PC+3]))<<8) + (np.uint32((SA2[PC+4]))<<0) )
            r27 = 0
            r28 = np.uint32(r10) ^ np.uint32(r28)
                    
            PC=PC+5        
            if Debug: print ("                                         r28: 0x%8.8x r27: 0x%8.8x r26: 0x%8.8x r25: 0x%8.8x r10: 0x%8.8x PC: 0x%8.8x"%(r28,r27,r26,r25,r10,PC))
 
        elif SA2[PC] == 0x49:
            if Debug: print ("SA2: PC=0x%2.2x Command: NEXT (0x%2.2x)"%(PC,SA2[PC]))
            PC=PC+1
            r26=r26-1
            if r26 != 0:
                PC=r25
 
        elif SA2[PC] == 0x4A:
            if Debug: print ("SA2: PC=0x%2.2x Command: BCC (0x%2.2x)"%(PC,SA2[PC]))
            r12 = SA2[PC+1]
            PC=PC+2
            if r27==0:
             PC=PC+r12
                     
        elif SA2[PC] == 0x68:
            if Debug: print ("SA2: PC=0x%2.2x Command: LOOP (0x%2.2x)"%(PC,SA2[PC]))
            r26 = SA2[PC+1]
            PC=PC+2
            r25=PC
       
        elif SA2[PC] == 0x93:
            if Debug: print ("SA2: PC=0x%2.2x Command: ADD (0x%2.2x)"%(PC,SA2[PC]))
            #print ("0x%8.8x"%( (np.uint32(SA2[PC+1]))<<24) )
            r10 = np.uint32( ((np.uint32(SA2[PC+1]))<<24) + (np.uint32((SA2[PC+2]))<<16) + (np.uint32((SA2[PC+3]))<<8) + (np.uint32((SA2[PC+4]))<<0) )            
            #r28= np.uint32( np.uint32(r28) + np.uint32(r10) ) # 32 bit aber numpi overflow error, ja ich weiss
            #r28= np.uint32( r28 + r10 ) # 32 bit aber numpi overflow error, ja ich weiss
            r28 = np.uint32(np.uint64(r28) + r10)  # 32 Bit ! dan halt so
            if r10 < r28:
                r27 = 0
            else:
                r27 = 1
            
            PC=PC+5
            if Debug: print ("                                         r28: 0x%8.8x r27: 0x%8.8x r26: 0x%8.8x r25: 0x%8.8x r10: 0x%8.8x PC: 0x%8.8x"%(r28,r27,r26,r25,r10,PC))
            
        else:
            if Debug: print ("SA2: PC=0x%2.2x Command: DONE (0x%2.2x)"%(PC,SA2[PC]))
            if Debug: print ("                                         r28: 0x%8.8x r27: 0x%8.8x r26: 0x%8.8x r25: 0x%8.8x r10: 0x%8.8x PC: 0x%8.8x"%(r28,r27,r26,r25,r10,PC))
            SeedVal=r28
            break 
    
    return SeedVal

def BLSeed2(SeedVal64):
                
                LookupArr1 =  [0x220B8BE7, 0xCA392FF8, 0xC1B02F0E, 0xD43C6CB3, 0x2D2500C7, 0x24537F70, 0x92DE086A, 0x9775DEAE, 
                               0x0F3541D5, 0x799A6042, 0x27C51066, 0xCF49F556, 0x068AAFE6, 0x05723330, 0xF2DDDC7C, 0x9DFEC0AA]
                eax_array =   [0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000]
                eax_array_ptr = 0
                
                esp_array =   [0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000,0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000,
                               0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000,0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000, 0x00000000]
                
                
                EDX=0x00000000
                
                
                #SeedVal64=0x1DBC61FB #Answer64=0xA0A0CAEC
                #SeedVal64=0x1B4C5F8A #Answer64=0xD80A247F
                ebx_10=SeedVal64+0x0B2B2B2B2
                
                print ("ebx_10: 0x%x type: %s" % (ebx_10,type(ebx_10))) 
                
                edx=0x1C
                
                for esi in range(0,6):
                    print("loop run: %d\n" % (esi))
                    
                    Work = ebx_10 >> edx
                    print ("SeedVal: 0x%x type: %s" % (Work,type(Work)))
                    Work = Work & 0x0F
                    print ("SeedVal: 0x%x type: %s" % (Work,type(Work)))
                    ebx_0 = LookupArr1[Work] # kein *4 weil aarray 4 byte groß ist
                    print ("ebx_0: 0x%x" % (ebx_0))
                    
                    edi = edx
                    edi = edi & 0xFF
                    ecx = edi
                    ecx = ecx - 4
                    
                    Work = ebx_10 >> ecx
                    ebx_4 = Work & 0x0F
                    print ("EBX[+4]: 0x%x" % (ebx_4))
                    
                    ecx = ecx - 4
                    Work = ebx_10 >> ecx
                    ebx_8 = Work & 0x0F                    
                    print ("EBX[+8]: 0x%x" % (ebx_8))
                    
                    Work =  ebx_0 >> ebx_4
                    print ("Work: 0x%x 0x%x" % (Work,ebx_4))
                    Work = (Work * ebx_8) & 0xFFFFFFFF # 32 Bit !
                    print ("Work: 0x%x 0x%x" % (Work,ebx_8))
                    Work = (Work + ebx_0) & 0xFFFFFFFF # 32 Bit !
                    print ("ebx_c: 0x%x 0x%x" % (Work,ebx_8))
                    ebx_c = Work
                    
                    ebx_10 = (ebx_10 + ebx_c) & 0xFFFFFFFF # 32 Bit !
                    print ("ebx_10: 0x%x" % (ebx_10))
                    
                    eax_array[eax_array_ptr] = ebx_10 
                    
                    edx = edx - (2+2) # "edx" identisch  zu "dl"
                    print ("edx bzw. dl = 0x%x" %(edx))
                
                    eax_array_ptr = eax_array_ptr + 1
                    
                print ("End Loop\n")    
                for element in eax_array:
                    print ("0x%8.8x"%(element))
                    
                Work = ebx_10 & 0xFF
                Work = Work  >> 4
                print ("Work: 0x%x" % (Work))
                ebx_0 = LookupArr1[Work] # kein *4 weil aarray 4 byte groß ist
                print ("ebx_0: 0x%x" % (ebx_0))                

                ebx_8 = ebx_10  >> 0x1C
                print ("ebx_8: 0x%x" % (ebx_8))

                ebx_4 = ebx_10 & 0x0F
                print ("ebx_4: 0x%x" % (ebx_4))
                
                Work = ebx_0 >> ebx_4
                Work = (Work * ebx_8) & 0xFFFFFFFF # 32 Bit !
                ebx_c = (Work + ebx_0) & 0xFFFFFFFF # 32 Bit !
                print ("ebx_c: 0x%x" % (ebx_c))
                
                ebx_10 = (ebx_10 + ebx_c) & 0xFFFFFFFF # 32 Bit !
                print ("ebx_10: 0x%x" % (ebx_10))
                
                esp_array[int(0x14/4)] = ebx_10
                
                Work = ebx_10 & 0x0F
                ebx_0 = LookupArr1[Work] # kein *4 weil aarray 4 byte groß ist
                print ("ebx_0: 0x%x" % (ebx_0))
                
                ebx_8 = ebx_10  >> 0x1C
                print ("ebx_8: 0x%x" % (ebx_8))
                
                ebx_4 = (ebx_10 >> 0x18) & 0x0F
                print ("ebx_4: 0x%x" % (ebx_4))
                
                Work = ebx_0 >> ebx_8
                print ("Work: 0x%x" % (Work))
                Work = (Work * ebx_4) & 0xFFFFFFFF # 32 Bit !
                ebx_c = (Work+ebx_0) & 0xFFFFFFFF # 32 Bit !
                print ("ebx_c: 0x%x" % (ebx_c))
                              
                Work = (eax_array[0] + eax_array[1]) ^ eax_array[2]
                Work = (Work + eax_array[3]) ^ eax_array[4] 
                Work = (Work + eax_array[5]) & 0xFFFFFFFF # 32 Bit !
                
                Work = Work ^ ebx_10
                Work = (Work + ebx_c) & 0xFFFFFFFF # 32 Bit !
                print ("Work: 0x%x" % (Work))
                Work = (Work + ebx_10) & 0xFFFFFFFF # 32 Bit !
                print ("Work: 0x%x" % (Work))
                
                Work_edx = 0x25478B3F >> 0x10
                print ("Work_edx: 0x%x" % (Work_edx))
                Work_edx = Work_edx + 0x00 # var_44
                
                Work_ecx = 0x25478B3F & 0x0FFFF
                print ("Work_ecx: 0x%x" % (Work_ecx))
                
                Work_edx = (Work_edx * Work_ecx) & 0xFFFFFFFF # 32 Bit !
                print ("Work_edx: 0x%x" % (Work_edx))
                
                Work = Work ^ Work_edx
                print ("SeedAnswer: 0x%8.8x" % (Work))
                return Work

def UDS_SecurityAccess2(bus,CanID):
        WorkingFrame = [0x27,0x01,0x00,0x00,0x00,0x00,0x00,0x00]
        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)        
        recv_message = bus.recv(0.01) # 0.2 s Timeout
        if recv_message != None:
            print (str( codecs.encode( bytearray(recv_message.data) ,'hex')) )
        
        SeedVal64 = (recv_message.data[2] << 24) + (recv_message.data[3] << 16) + (recv_message.data[4] << 8) + recv_message.data[5]
        print("BlSeed2Val: 0x%8.8x" %(SeedVal64))
        SeedAnswer = BLSeed2(SeedVal64)
        print("BlSeed2Answer: 0x%8.8x" %(SeedAnswer))
        
        WorkingFrame = [0x27,0x02,(SeedAnswer&0xFF000000)>>24,(SeedAnswer&0xFF0000)>>16,(SeedAnswer&0xFF00)>>8,(SeedAnswer&0xFF),0x00,0x00]
        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)        
        recv_message = bus.recv(0.01) # 0.2 s Timeout
        if recv_message != None:
            print (str( codecs.encode( bytearray(recv_message.data) ,'hex')) )        

def UDS_TesterPresent(bus,CanID):
        WorkingFrame = [0x02,0x3E,0x00]
        WorkingFrame = FillUpCanFrame(WorkingFrame)
        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)
        for receive_counter in range (0,10): # 10 frames empfangen
            recv_message = bus.recv(0.01) # 0.2 s Timeout
            if recv_message != None:
                if recv_message.data[0] == 0x02 and recv_message.data[1] == 0x7E:
                    #print("ID 0x%3.3x " % (CanID),end='')
                    #print (recv_message)
                    break


def UDS_Receive(bus: can.bus.BusABC, CanID: int, buf=" "):
        SingleFrame = False

        while True:
         recv_message = bus.recv(2.0) # 2 s Timeout
         if recv_message == None:
             print("Timeout")
             return None
         if recv_message.arbitration_id == 0x30c:  #workaround für MQB X FW
                #print("Workaround for MQB 0x30c")
                continue

         #print (str(binascii.hexlify(recv_message.data)))
         #print (str((recv_message.arbitration_id)))
        
         #check for UDS 0x78 requestCorrectlyReceived-ResponsePending 
         if    recv_message.data[0] & 0b11110000 == 0x00 \
           and recv_message.data[1] == 0x7F  \
           and recv_message.data[3] == 0x78:
               #print ("requestCorrectlyReceived-ResponsePending retry recv ...")
               print (" repeat ",end='')
               ##recv_message = bus.recv(2.0) # 2 s Timeout
               ##if recv_message == None:
               ##       print("UDS_Receive requestCorrectlyReceived-ResponsePending retry recv ... Timeout")
               ##       return ["UDS_Receive requestCorrectlyReceived-ResponsePending retry recv ... Timeout"]               
         else:
           if recv_message.data[0] == 0x30 and recv_message.data[1] == 0x0F:
            pass
            #SingleFrame = True
            #SizeDataToReveive = recv_message.data[0]
           else:
            break

        
        if recv_message.data[0] == 0x10:    #(FF) First Frame
         SizeDataToReveive = recv_message.data[1]
         UDS_SID = recv_message.data[2]

        if (recv_message.data[0] & 0b11110000) == 0x0: #(SF) Single Frame
         SingleFrame = True
         SizeDataToReveive = recv_message.data[0]
         #SizeDataToReveive = SizeDataToReveive - 7 # max 7 sind im ersten Frame drinn
         UDS_SID = recv_message.data[1]

        #if recv_message.data[0] & 0b11110000 == 0x20: #(CF) Consecutive Frame

        #print ("DataSize= 0x%4.4x " % (SizeDataToReveive),end='')
        #print (" UDS_SID= 0x%2.2x " % (UDS_SID),end='')
        DataReceived = recv_message.data

        #if UDS_SID == 0x7F: #Error, nur 1 Frame
        if recv_message.data[1] == 0x7F: #Error, nur 1 Frame
            #if recv_message.data[3] != 0x31:
            boolQuiet = True
            if not boolQuiet == True: # geht so leider nicht
             #pass
             print(buf + "   ServiceIdRQ 0x%2.2x ErrorCode NRC 0x%2.2x" % (recv_message.data[2],recv_message.data[3]),end='\n')
            return []
        
        
        print (buf,end='')
        

        if SingleFrame == True:
         #sigle antwort
         #print("Single Antwort")
         pass

        else:
         #ACK  #2021 ACC Read Public Key workaround: i guess: read buffer was increaded
         #msg = can.Message(arbitration_id=CanID,data=[0x30, 0x10, 0x00, 0x00, 0x00, 0x00,0x00,0x00],is_extended_id=False)
         msg = can.Message(arbitration_id=CanID,data=[0x30, 0x00, 0x01, 0x00, 0x00, 0x00,0x00,0x00],is_extended_id=False)
         bus.send(msg)

         SizeDataToReveive = SizeDataToReveive - 6 # 6 sind im ersten Frame drinn
         #multiple antwort frames
         while (SizeDataToReveive > 0):
          recv_message = bus.recv(2.0) # 2 s Timeout

          if recv_message.arbitration_id == 0x30c:  #workaround für MQB X FW
             #print("Workaround for MQB 0x30c")
             continue

          #print (recv_message)
          #print (str(binascii.hexlify(recv_message.data)))
          DataReceived = DataReceived + recv_message.data
          SizeDataToReveive = SizeDataToReveive - 7

        return UDS_ReceiveDecodeAndRemovePadding(DataReceived)

def UDS_ReadDataByIdentifier(bus,CanID,Identifier,Counter=-1):
          buf = ("ReadDataByIdentifier ID: " + str(hex(Identifier)) +" "+ str(hex(Counter))+ " ")
          IdentifierHighByte,IdentifierLowByte = SplitToBytes(Identifier)
          WorkingFrame = [0x03,0x22,IdentifierHighByte,IdentifierLowByte]
          if Counter != -1:
           WorkingFrame[0] = 0x04
           WorkingFrame =  WorkingFrame + [Counter]  
           
          WorkingFrame = FillUpCanFrame(WorkingFrame)

          msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
          bus.send(msg)
          return UDS_Receive(bus,CanID,buf)
      
#def UDS_RequestUpload(bus,CanID,Type):
#        WorkingFrame = [0x10,0x0B,0x35,Type,0x44,0x03,0xFF,0x19]
#        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
#        bus.send(msg)
#        recv_message = bus.recv(2.0) # 2 s Timeout        
#        print(recv_message)
#
#        WorkingFrame = [0x21,0x00,0x00,0x00,0x00,0x20] 
#        WorkingFrame = FillUpCanFrame(WorkingFrame)

#        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
#        bus.send(msg)
#        recv_message = bus.recv(2.0) # 2 s Timeout        
#        print(recv_message)

#        return

def UDS_RequestUpload(bus,CanID,DataPayload):
        FrameNr=0
        DataToSendPtr=0
        DataSize = len(DataPayload)
        print("UDS_RequestUp DataPayload Size: " + hex(DataSize))        
        #WorkingFrame = [0x10,0x0B,0x34,0x01,0x44,0x03,0xFF,0x19]
        if DataSize > 5:
           WorkingFrame = [0x10,DataSize+1,0x35] + DataPayload[DataToSendPtr:DataToSendPtr+5]
           DataToSendPtr=DataToSendPtr+5 # 5 Bytes gesendet
        else: # =< 5 nur 1 Frame
           WorkingFrame = [DataSize+1,0x35] + DataPayload[DataToSendPtr:DataToSendPtr+DataSize]
           WorkingFrame = FillUpCanFrame(WorkingFrame)

        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)
        recv_message = bus.recv(2.0) # 2 s Timeout        

        if DataSize > 5:
           FrameNr=FrameNr+1
           WorkingFrame = [0x20+FrameNr] +  DataPayload[DataToSendPtr:DataToSendPtr+5]
           WorkingFrame = FillUpCanFrame(WorkingFrame)
           msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
           bus.send(msg)  
           recv_message = bus.recv(2.0) # 2 s Timeout            
        else:
          pass


def UDS_RequestDownload(bus,CanID,DataPayload):
        FrameNr=0
        DataToSendPtr=0
        DataSize = len(DataPayload)
        print("UDS_RequestDownload DataPayload Size: " + hex(DataSize))        
        #WorkingFrame = [0x10,0x0B,0x34,0x01,0x44,0x03,0xFF,0x19]
        WorkingFrame = [0x10,DataSize+1,0x34] + DataPayload[DataToSendPtr:DataToSendPtr+5]
        DataToSendPtr=DataToSendPtr+5 # 5 Bytes gesendet
        
        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)
        recv_message = bus.recv(2.0) # 2 s Timeout        
        FrameNr=FrameNr+1
        #WorkingFrame = [0x20+FrameNr,0x00 ,0x00 ,0x00 ,0x06 ,0x00] 
        WorkingFrame = [0x20+FrameNr] +  DataPayload[DataToSendPtr:DataToSendPtr+5]
        
        WorkingFrame = FillUpCanFrame(WorkingFrame)
   
        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)  
        recv_message = bus.recv(2.0) # 2 s Timeout            
        if recv_message.data[1] == 0x7F: 
            print("   ServiceIdRQ 0x%2.2x ErrorCode NRC 0x%2.2x" % (recv_message.data[2],recv_message.data[3]),end='\n')
            return False
            #sys.exit(0)
        return True


def UDS_TransferData(bus,CanID,DataPayload):
        WorkingFrame = []
        DataSize = len(DataPayload)
        print("UDS_TransferData DataPayload Size: " + hex(DataSize))

        if DataSize>0x70:
            DataPosEndThisBlock = 256
            DataSizeThisBlock = 256
        else:
            DataPosEndThisBlock = DataSize
            DataSizeThisBlock = DataSize
            
        BlockNumber=1       
        DataToSendPtr=0

        while (DataToSendPtr < DataSize):
            print("UDS_TransferData Transfer Block     : " +hex(BlockNumber))
            print("UDS_TransferData DataPosEndThisBlock: " +hex(DataPosEndThisBlock))
            print("UDS_TransferData DataSizeThisBlock  : " +hex(DataSizeThisBlock))
            print("Data: 0x%2.2x "%(BlockNumber),end='')
            for lauf in range (0,DataSizeThisBlock):
             print ("0x%2.2x " % (DataPayload[lauf+(BlockNumber-1)*256]),end='')
            print("")

            FrameNr=0
            CanFrameDataSizeHigh,CanFrameDataSizeLow = SplitToBytes(DataSizeThisBlock+2)
            
            WorkingFrame = [0x10+CanFrameDataSizeHigh,CanFrameDataSizeLow,0x36,BlockNumber] + DataPayload[DataToSendPtr:DataToSendPtr+4]
            DataToSendPtr=DataToSendPtr+4 # 4 Bytes gesendet
            msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
            bus.send(msg)
            recv_message = bus.recv(2.0) # 2 s Timeout
           
            while(DataToSendPtr < DataPosEndThisBlock):
               FrameNr=FrameNr+1
               if FrameNr==16: FrameNr=0
               #print("Sending Multiple Frames: ConsecutiveFrame (CF) Frame: " + str(FrameNr))
               #print("Data Left: " + str(DataPosEndThisBlock-DataToSendPtr))
               
               WorkingFrame = [0x20+FrameNr] + DataPayload[DataToSendPtr:DataToSendPtr+7]  #<=== DAAAAAA F E H L E R
               WorkingFrame = FillUpCanFrame(WorkingFrame)
               #print(WorkingFrame)
               DataToSendPtr=DataToSendPtr+7 # 7 Bytes gesendet
               msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
               bus.send(msg)
               sleep(0.005)  
               
            UDS_Receive(bus,CanID)
               
            DataPosEndThisBlock = DataPosEndThisBlock + 256
            if (DataPosEndThisBlock > DataSize):
             DataPosEndThisBlock = DataSize # last block
             DataSizeThisBlock = DataPosEndThisBlock-DataToSendPtr
            BlockNumber = BlockNumber+1

def UDS_TransferExit(bus,CanID):
        WorkingFrame = [0x01,0x37]
        WorkingFrame = FillUpCanFrame(WorkingFrame)
        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)
        recv_message = bus.recv(2.0) # 2 s Timeout        

def UDS_RoutineControl2(bus,CanID,Ctrltype,CtrlPayload):
    # Ctrltype
    #  0x01 Start
    #  0x02 Stop
    #  0x03 RequestResult
    DataSize = len(CtrlPayload)
    print("CtrlPayload Size: " + hex(DataSize))
    DataToSendPtr=0
    FrameNr=0
    
    WorkingFrame = [0x10,DataSize+2,0x31,Ctrltype] + CtrlPayload[DataToSendPtr:DataToSendPtr+4] #,0x02, 0x02, 0x04, 0x03] # 0x8b Size = 6 Byte im ersten frame + 0x13 7 byte Frames
    DataToSendPtr=DataToSendPtr+4 # 4 Bytes gesendet
    msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
    bus.send(msg)
    recv_message = bus.recv(2.0) # 2 s Timeout    
    while(DataToSendPtr < DataSize):
       if FrameNr<0xF:
           FrameNr=FrameNr+1
       else:
           FrameNr=0
       
       #print("Sending Multiple Frames: ConsecutiveFrame (CF) Frame: " + str(FrameNr))
       WorkingFrame = [0x20+FrameNr] + CtrlPayload[DataToSendPtr:DataToSendPtr+7]
       DataToSendPtr=DataToSendPtr+7 # 7 Bytes gesendet
       msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
       bus.send(msg)  
       if FrameNr==0xF:
           recv_message = bus.recv(2.0) # 2 s Timeout
           #sleep(1)
       
    UDS_Receive(bus,CanID)    
    

def UDS_WriteDataByIdentifier(bus,CanID,Identifier,DataList):
        WorkingFrame = []
        #print(CanID)
        #print(Identifier)
        #print(DataList)
        #for BYTE in DataList:
        # print (format(BYTE,'02x'),end = '')
        #print("")

        DataSize = len(DataList)
        #print("Size Data: " + str(DataSize));

        IdentifierHighByte,IdentifierLowByte = SplitToBytes(Identifier)

        if DataSize > 4: # mehr als 4 bytes ==> mehr als 1 Frame
          #print("Sending Multiple Frames: FirstFrame (FF)")
          FrameNr=0
          DataToSendPtr=0
          #TODO Mehr als 0xFF Bytes
          WorkingFrame = [0x10,DataSize+3,0x2E,IdentifierHighByte,IdentifierLowByte] + DataList[DataToSendPtr:DataToSendPtr+3]
          DataToSendPtr=DataToSendPtr+3 # 3 Bytes gesendet
          msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
          bus.send(msg)
          recv_message = bus.recv(2.0) # 2 s Timeout
          #print (recv_message)

          while(DataToSendPtr < DataSize):
           FrameNr=FrameNr+1
           if FrameNr==16: FrameNr=0
           #print("Sending Multiple Frames: ConsecutiveFrame (CF) Frame: " + str(FrameNr))
           WorkingFrame = [0x20+FrameNr] + DataList[DataToSendPtr:DataToSendPtr+7]
           DataToSendPtr=DataToSendPtr+7 # 7 Bytes gesendet
           if len(WorkingFrame) < 8: 
            WorkingFrame = FillUpCanFrame(WorkingFrame)

           msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
           sleep(0.05)
           bus.send(msg)


        else: # Single Frame (CS)
          #print("Sending Single Frame (CS)")
          WorkingFrame = [DataSize+3,0x2E,IdentifierHighByte,IdentifierLowByte] + DataList
          WorkingFrame = FillUpCanFrame(WorkingFrame)

          msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
          bus.send(msg)
          recv_message = bus.recv(2.0) # 2 s Timeout
          #print (recv_message)
          return recv_message

        #Message Send, receive Answer
        return UDS_Receive(bus,CanID)


def WriteCPData(bus,CPData,CPDatum,CPDevice,CPID):
        #TmpData = UDS_ReadDataByIdentifier(bus,0x714,0xF19E)
        #del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
        #print(TmpData)

        #TmpData = UDS_ReadDataByIdentifier(bus,0x714,0xF1A2)
        #del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
        #print(TmpData)
	#yxcv

        #recv_message = UDS_WriteDataByIdentifier(bus,0x714,0x00BE,CPData)
        #if len(recv_message) != 0x00:
        # if recv_message[0] == 0x00 and recv_message[1] == 0xbe:
        #    print(" Write CP Data OK")
        #else:
        # print(" Write CP Data Error")
        # print(recv_message)
        #sys.exit(0)

        #nicht bei acc
        #tmp2arr2 = ( UDS_ReadDataByIdentifier(bus,CPDevice,0x0956) )
        #print (tmp2arr2,end='')
        #print (str( codecs.encode( tmp2arr2 ,'hex')) )

        UDS_TesterPresent(bus,CPDevice)

        tmp2arr2 = ( UDS_ReadDataByIdentifier(bus,CPDevice,0xF19E) )
        print (tmp2arr2,end='')
        print (str( codecs.encode( tmp2arr2 ,'hex')) )

        tmp2arr2 = ( UDS_ReadDataByIdentifier(bus,CPDevice,0xF1A2) )
        print (tmp2arr2,end='')
        print (str( codecs.encode( tmp2arr2 ,'hex')) )

        tmp2arr2 = ( UDS_ReadDataByIdentifier(bus,CPDevice,0xF17C) )
        print (tmp2arr2,end='')
        print (str( codecs.encode( tmp2arr2 ,'hex')) )

        UDS_DiagnosticSessionControl(bus,CPDevice,0x03)

        UDS_WriteDataByIdentifier(bus,CPDevice,0xF198,[0x00,0x00,0x00,0x00,0x00,0x2E])

        UDS_WriteDataByIdentifier(bus,CPDevice,0xF199,CPDatum)

        recv_message = UDS_WriteDataByIdentifier(bus,CPDevice,CPID,CPData)
        if len(recv_message) != 0x00:
         if recv_message[0] == 0x00 and recv_message[1] == 0xbe:
            print(" Write CP Data OK")
        else:
         print(" Write CP Data Error")
         print(recv_message)
         print("Ret: %x %x %x %x"%(recv_message[0],recv_message[1],recv_message[2],recv_message[3]))

        #TmpData = recv_message
        #print(TmpData,end='')
        #print( str( codecs.encode( bytearray(TmpData) ,'hex') ) ) 

def UDS_ReadMemoryByAddress(bus,CanID,Addr3,Addr2,Addr,Size):
        AddrHi,AddrLo = SplitToBytes(Addr)
        WorkingFrame = [0x07,0x23,0x14,Addr3,Addr2,AddrHi,AddrLo,Size]
        WorkingFrame = FillUpCanFrame(WorkingFrame)
        msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)
        return UDS_Receive(bus,CanID)
    
def UDS_WriteMemoryByAddress(bus,CanID,Addr3,Addr2,Addr,DataList):
        #AddrHi,AddrLo = SplitToBytes(Addr)
        #WorkingFrame = [0x07,0x3D,0x14,Addr3,Addr2,AddrHi,AddrLo,DataList[0]]
        #WorkingFrame = FillUpCanFrame(WorkingFrame)
        #msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
        #bus.send(msg)    
        #return UDS_Receive(bus,CanID)  
        WorkingFrame = []

        DataSize = len(DataList)

        DataSizeHi,DataSizeLo=SplitToBytes(DataSize)
        AddrHi,AddrLo = SplitToBytes(Addr)

        if DataSize > 0: # mehr als 0 bytes ==> mehr als 1 Frame :)
          #print("Sending Multiple Frames: FirstFrame (FF)")
          FrameNr=0
          DataToSendPtr=0
          WorkingFrame = [0x10+DataSizeHi,DataSizeLo+8,0x3D,0x24,Addr3,Addr2,AddrHi,AddrLo]
          #DataToSendPtr=DataToSendPtr+0 # 0 Bytes gesendet
          msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
          bus.send(msg)
          recv_message = bus.recv(2.0) # 2 s Timeout
          #print (recv_message)
          firstFrame=True

          while(DataToSendPtr < DataSize):
           FrameNr=FrameNr+1
           if FrameNr==16: FrameNr=0
           print("Sending Multiple Frames: ConsecutiveFrame (CF) Frame: " + str(FrameNr))
           sleep(0.01)
           if firstFrame == True:
            WorkingFrame = [0x20+FrameNr,DataSizeHi,DataSizeLo] + DataList[DataToSendPtr:DataToSendPtr+5]
            DataToSendPtr=DataToSendPtr+5 # 6 Bytes gesendet
            firstFrame=False 
           else:
            WorkingFrame = [0x20+FrameNr] + DataList[DataToSendPtr:DataToSendPtr+7]
            DataToSendPtr=DataToSendPtr+7 # 7 Bytes gesendet
           
           if len(WorkingFrame) < 8: 
            WorkingFrame = FillUpCanFrame(WorkingFrame)

           msg = can.Message(arbitration_id=CanID,data=WorkingFrame,is_extended_id=False)
           bus.send(msg)

        #Message Send, receive Answer
        return UDS_Receive(bus,CanID)    
    
def TachoExportCP(bus):

        for Addr in range(0x1500,0x1700,0x20):
         TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x04,0x00,Addr,0x20)
         print( " "+str(str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ))) 
    

def TachoIDString(bus):
        ##/SW509 kann das  icht
        #retStrg ="SW509"
        #return retStrg

        TmpData = UDS_ReadDataByIdentifier(bus,0x714,0xF190)
        del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
        #print(TmpData,end= '  ')
        retStrg = str(bytearray(TmpData),'utf-8')

        TmpData = UDS_ReadDataByIdentifier(bus,0x714,0xF17C)
        del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg            
        retStrg = retStrg + "_" + str(bytearray(TmpData),'utf-8')

        TmpData = UDS_ReadDataByIdentifier(bus,0x714,0xF189)
        del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg            
        retStrg = retStrg + "_SW" + str(bytearray(TmpData),'utf-8')

        return retStrg    

def TachoDumpRam(bus,FilenamePrefix):
        now = datetime.now()
        dt_string = now.strftime("%d.%m.%Y.%H.%M.%S")
        
        f = open(FilenamePrefix + "_" + dt_string +'_TachoRAM.bin', 'w+b')
        
        for Tel in range(255,256):
         for Sel in range(255,256):
          for Addr in range(0x0000,0xFFFF,0x20):
            if Addr == 0xf560: # Read ==> Tacho Reset
             f.write(bytearray([0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77,0x77]))    
            else:
             TmpData = UDS_ReadMemoryByAddress(bus,0x714,Tel,Sel,Addr,0x20)
             #print(TmpData,end='')
             print( " "+str(hex(Tel))+" "+str(hex(Sel))+" "+str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )
             f.write(TmpData)
        f.close()    

def TachoDump3DFlash(bus,FilenamePrefix):
        now = datetime.now()
        dt_string = now.strftime("%d.%m.%Y.%H.%M.%S")
        
        f = open(FilenamePrefix + "_" + dt_string +'_Tacho3DFlash.bin', 'w+b')    
        for UpperAddr in range (0x00,0xFE,0x01):
         print(" "+str(hex(UpperAddr)))
         for Addr in range(0x0000,0xFFFF,0x40):            
            TmpData = UDS_ReadMemoryByAddress(bus,0x714,0xBF,UpperAddr,Addr,0x40)
            #print(" "+str(hex(UpperAddr))+" "+str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') )) 
            f.write(TmpData)

        f.close()

def TachoDump3DCode(bus,FilenamePrefix):
        print("")
        print("T O D O: GEHT NICHT !!! 2022.01")
        print("")
        now = datetime.now()
        dt_string = now.strftime("%d.%m.%Y.%H.%M.%S")
        
        f = open(FilenamePrefix + "_" + dt_string +'_Tacho3DCode.bin', 'w+b')    
        for UpperAddr in range (0x00,0x02,0x01): 
         print(" "+str(hex(UpperAddr)))
         for Addr in range(0x0000,0xFFFF,0x01):            
            TmpData = UDS_ReadMemoryByAddress(bus,0x714,0xC0,UpperAddr,Addr,0x20)
            print(" "+str(hex(UpperAddr))+" "+str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') )) 
            f.write(TmpData)

        f.close()


def TachoDumpEeprom(bus: can.bus.BusABC, FilenamePrefix: str):
        now = datetime.now()
        dt_string = now.strftime("%d.%m.%Y.%H.%M.%S")
        
        f = open(FilenamePrefix + "_" + dt_string +'_TachoEeprom.bin', 'w+b')    
        for Addr in range(0x0000,0x2000,0x20):            
            TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x04,0x00,Addr,0x20)
            print( " "+str(str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ))) 
            f.write(TmpData)
        f.close()


def TachoDumpFlash(bus: can.bus.BusABC, FilenamePrefix: str):
        now = datetime.now()
        dt_string = now.strftime("%d.%m.%Y.%H.%M.%S")
        
        f = open(FilenamePrefix + "_" + dt_string +'_TachoFlash_0-1FFFF.bin', 'w+b')
        for UpperByte in range (0x00,0x20):
         for Addr in range(0x0000,0x10000,0x40):            
            TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x00,UpperByte,Addr,0x40)
            print( " "+str(str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ))) 
            f.write(TmpData)
        f.close()              

def TachoDumpCpKeyRAM(bus):

        TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x03DE)
        print("Acc CP Error Counter: " +str(codecs.encode( bytearray(TmpData[2:4]) ,'hex') ))
        TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x3C0A)
        print("Acc CP VCRN: " +str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))
        TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x3C05)
        print("Acc Pub Key: " +str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))
        TmpData = UDS_ReadDataByIdentifier(bus,0x757,0xF190)
        print("Acc VINHex: " +str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))
        print("Acc VIN   : " +str(bytearray(TmpData[2:]) ,'utf-8') )
        TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x3C00)
        print("Acc FEC: " +str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))
        print("ACC FEC1: " +str(codecs.encode( bytearray(TmpData[2:7]) ,'hex') ))
        print("ACC FEC2: " +str(codecs.encode( bytearray(TmpData[7:12]) ,'hex') ))
        print("ACC FEC3: " +str(codecs.encode( bytearray(TmpData[12:17]) ,'hex') ))
        print("ACC FEC4: " +str(codecs.encode( bytearray(TmpData[17:22]) ,'hex') ))
        print("ACC FEC5: " +str(codecs.encode( bytearray(TmpData[22:27]) ,'hex') ))
        print("")

        TmpData = UDS_ReadDataByIdentifier(bus,0x714,0xF190)
        print("Cluster VINHex: " +str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))
        print("Cluster VIN   : " +str(bytearray(TmpData[2:]) ,'utf-8') )
        print("")
        
        TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x00,0x01,0x0034,0x10)
        print( " CP AES Key @ Flash 0x10034: " +str( codecs.encode( bytearray(TmpData) ,'hex') )) 
        print("")
        print("Eeprom @ 0x1500")

        TachoExportCP(bus)
        #wkkk
        ArraySWVersionToAddrInRam = [[0x1008,0x1104,0x1104,0x1105,0x1109,0x2030,0x2030,0x2030,0x1104],
                                     [0xC105,0xC525,0xb8bd,0xC3CD,0xC531,0xba1d,0xc521,0xc691,0xbd09]]

        SWVersion = UDS_ReadDataByIdentifier(bus,0x714,0xF189)
        del SWVersion[0:2] # die zwei Byte response ID müssen hier noch weg
        print("")
        SWVersion_Work = (int.from_bytes(binascii.unhexlify(SWVersion),byteorder='big',signed=False))

        SwNotInTable = True

        for i in range(len(ArraySWVersionToAddrInRam[0])):
          if ArraySWVersionToAddrInRam[0][i] == SWVersion_Work:
            SwNotInTable = False 
            Addr = ArraySWVersionToAddrInRam[1][i]
            print ("SW Version 0x%x found in Table, Addr of UDS AES Key in Ram: 0x%0x" %(SWVersion_Work,Addr))
            print ("Reading Ram ...")
            TmpData = UDS_ReadMemoryByAddress(bus,0x714,255,255,Addr,0x10)
            print( "UDS Aes Key: "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )
            print("")

            for Addr in [Addr,Addr+18,Addr+18+18,Addr+18+18+18]:
              TmpData = UDS_ReadMemoryByAddress(bus,0x714,255,255,Addr,0x10)
              print( " " +str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )
              TmpData = UDS_ReadMemoryByAddress(bus,0x714,255,255,Addr+0x10,0x2)
              print( " " +str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )

        if SwNotInTable:
          print ("Error SW: 0x%x is not in Table, do a FlashRead and extract address"%(SWVersion_Work))
          sys.exit(1)


def EnableEngeneeringMode(bus):
        msg = can.Message(arbitration_id=0x714,data=[0x02, 0x10, 0x60, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA],is_extended_id=False)
        bus.send(msg)
        #print("Message sent on {}".format(bus.channel_info))
        recv_message = bus.recv(2.0) # 2 s Timeout
        #print (recv_message)
        UDS_WriteDataByIdentifier(bus,0x714,0xFD11,[0x01])
        UDS_WriteDataByIdentifier(bus,0x714,0xFD11,[0x06])
        msg = can.Message(arbitration_id=0x714,data=[0x30, 0x10, 0x00, 0x00, 0x00, 0x00,0x00,0x00],is_extended_id=False)
        bus.send(msg)
        recv_message = bus.recv(2.0) # 2 s Timeout
        #print (recv_message)
        SeedVomTacho = UDS_WriteDataByIdentifier(bus,0x714,0xFD11,SendSeedRequest)
        #recv_message = bus.recv(2.0) # 2 s Timeout
        #print (recv_message)
        #SeedVomTacho = recv_message.data
        #msg = can.Message(arbitration_id=0x714,data=[0x30, 0x10, 0x00, 0x00, 0x00, 0x00,0x00,0x00],is_extended_id=False)
        #bus.send(msg)
        #recv_message = bus.recv(2.0) # 2 s Timeout
        #print (recv_message)
        #SeedVomTacho = SeedVomTacho + recv_message.data
        #recv_message = bus.recv(2.0) # 2 s Timeout
        #print (recv_message)
        #SeedVomTacho = SeedVomTacho + recv_message.data
        #recv_message = bus.recv(2.0) # 2 s Timeout
        #print (recv_message)
        #SeedVomTacho = SeedVomTacho + recv_message.data

        UDS_TesterPresent(bus,0x714)

        #SeedVomTacho = UDS_ReceiveDecodeAndRemovePadding(SeedVomTacho)

        #print("SeedVomTacho: " + str(binascii.hexlify(SeedVomTacho)))
        #print("SeedVomTacho[0..15]: " + str(binascii.hexlify(SeedVomTacho[0:16])))

        #print (len(SeedVomTacho))

        #print(binascii.hexlify(bytearray(SendSeedRequest)))

        #codecs.decode(keyhex, 'hex')

        iv= codecs.decode(binascii.hexlify(bytearray(SendSeedRequest[1:17])), 'hex')
        #print (iv)
        #print (len(iv))
        aes = pyaes.AESModeOfOperationCBC(key, iv = iv)
        plaintext = codecs.decode(binascii.hexlify(bytearray(SeedVomTacho[0:16])), 'hex')
        ciphertext = aes.encrypt(plaintext)

        iv= ciphertext
        aes = pyaes.AESModeOfOperationCBC(key, iv = iv)
        #print (type(SeedVomTacho))
        #print (type(SendSeedRequest))
        #print (type([0x01]))

        plaintext = codecs.decode(binascii.hexlify(bytearray(list(SeedVomTacho[16:23])+SendSeedRequest[17:25]+[0x01])), 'hex') 
        #print (plaintext)
        #print (len(plaintext))
        #print (len(list(SeedVomTacho[16:23])))
        #print (len(SendSeedRequest[18:26]))
        #print (len(SendSeedRequest))
        ciphertext2 = aes.encrypt(plaintext)

        UDS_WriteDataByIdentifier(bus,0x714,0xFD11,([0x04]+list(ciphertext)+list(ciphertext2)))

        UDS_TesterPresent(bus,0x714)

        recv_message = UDS_WriteDataByIdentifier(bus,0x714,0xFD11,[0x01])
        #print (recv_message.data)
        #print (recv_message.data[2])
        if recv_message.data[2] == 0x07:
          print ("Engeneering Mode Access OK")
          return True
        else:
          print ("Error entering Engeneering mode")
          return False

def MenuTacho(bus1,i,u,switch):
                istr= "%2.2x" % (i)
                ustr= "%2.2x" % (u)
                
                if switch == True:
                 bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('80204C55'+ustr+'526F62', 'hex'),is_extended_id=False))
                 recv_message = bus1.recv(1.0)
                 bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('C065727420212121', 'hex'),is_extended_id=False))
                 recv_message = bus1.recv(1.0)
                 bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('C120204152'+istr+'5250', 'hex'),is_extended_id=False))
                 recv_message = bus1.recv(1.0)
                 bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('C24D20'+istr+istr+'202033', 'hex'),is_extended_id=False))
                 recv_message = bus1.recv(1.0)
                 #bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('C33030300C303132', 'hex'),is_extended_id=False))
                 #recv_message = bus1.recv(1.0)
                 bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('4C5000000000', 'hex'),is_extended_id=False))
                 recv_message = bus1.recv(1.0)
                else:
                 bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('80204C55'+ustr+'4B6E6F', 'hex'),is_extended_id=False))
                 recv_message = bus1.recv(1.0)
                 bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('C065727420212121', 'hex'),is_extended_id=False))
                 recv_message = bus1.recv(1.0)
                 bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('C120204152'+istr+'5250', 'hex'),is_extended_id=False))
                 recv_message = bus1.recv(1.0)
                 bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('C24D20'+istr+istr+'202033', 'hex'),is_extended_id=False))
                 recv_message = bus1.recv(1.0)
                 #bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('C33030300C303132', 'hex'),is_extended_id=False))
                 #recv_message = bus1.recv(1.0)
                 bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('4C5000000000', 'hex'),is_extended_id=False))
                 recv_message = bus1.recv(1.0)

def TP20_Send(bus,arbitration_id,data):
   global TP20Counter
   if TP20Counter == 0x10: TP20Counter = 0x00
   data[0] = data[0] + TP20Counter
   msg = can.Message(arbitration_id=arbitration_id,data=data,is_extended_id=False)
   bus.send(msg)
   TP20Counter = TP20Counter + 1

def TP20_SendACK(bus,arbitration_id,LastCounter=0):
   myLastCounter=(LastCounter&0x0F)+1
   if myLastCounter == 0x10: myLastCounter = 0x00
   msg = can.Message(arbitration_id=arbitration_id,data=[0xB0+myLastCounter],is_extended_id=False)
   bus.send(msg)

def TP20_SecurityAccess(bus,arbitration_id,Magic,Type=0x03):
   ## 5/6
   #WorkingFrame = [0x10,0x00,0x02,0x27,0x03] #APP
   #WorkingFrame = [0x10,0x00,0x02,0x27,0x01] #Boot
   WorkingFrame = [0x10,0x00,0x02,0x27]
   WorkingFrame.append(Type) 
   print("Using Login %5.5d   Type %d "%(Magic,Type),end='\n')
   TP20_Send(bus,arbitration_id,WorkingFrame)

   Seed = TP20_HandleReturn(bus,arbitration_id,0x00)
   SeedVal64 = int.from_bytes(Seed,byteorder='big', signed=False)
   print(" ... got Seed: 0x%8.8x %d" %(SeedVal64,SeedVal64) ,end='\n')
   SeedVal = np.int64(SeedVal64)
   
   if Type==0x03: #APP
    SeedAnswer = SeedVal + Magic
   else: #Boot 
    SA2 = codecs.decode('6807814A05870E442763494C', 'hex')
    SeedAnswer = Tacho_SA2_Seed_Calc(SeedVal,SA2,Debug=False)

   print(" ... Answer:   0x%8.8x %d" %(SeedAnswer,SeedAnswer),end='\n')
   sleep(0.01)
   SeedValAnswerByteArr =  int(SeedAnswer).to_bytes(4, byteorder='big') 
   WorkingFrame = [0x20,0x00,0x06,0x27]
   WorkingFrame.append(Type+1)
   WorkingFrame = WorkingFrame + list(SeedValAnswerByteArr[0:3])
   #WorkingFrame = [0x20,0x00,0x06,0x27,0x04]+ list(SeedValAnswerByteArr[0:3]) #APP
   #WorkingFrame = [0x20,0x00,0x06,0x27,0x02]+ list(SeedValAnswerByteArr[0:3]) #Boot
   TP20_Send(bus,arbitration_id,WorkingFrame)
   sleep(0.01)
   WorkingFrame = [0x10]+ list(SeedValAnswerByteArr[3:4])
   TP20_Send(bus,arbitration_id,WorkingFrame)
   TP20_HandleReturn(bus,arbitration_id,0x00)
   sleep(0.01)

def KWP2000_ServiceIdToString(ServiceID):
   #KWP2000 Bosch Infos 
   #From https://automotivetechis.files.wordpress.com/2012/06/presentation_debrecen_en_2008_03_27.pdf
   ListKWP2000Services = [ 
[0x09,"??"				,"0x89"],
[0x10,"StartDiagnosticSession"		,"0x89"],
[0x11,"ECUReset"			,"  ??"],
[0x12,"ReadFreezeFrameData"		,"0x89"],
[0x13,"ReadDiagnosticTroubleCode"	,"  ??"],
[0x14,"ClearDiagnosticInformation"	,"0x89"],
[0x17,"ReadStatusOfDiagnosticCode"	,"  ??"],
[0x18,"ReadDiagnosticTroubleCodeByStatus","0x89"],
[0x20,"StopDiagnosticSession"		,"0x89"],
[0x21,"ReadDataByLocalIdentification"	,"0x89"],
[0x22,"ReadDataByCommonID"		,"0x89"],
[0x23,"ReadMemoryByAddress"		,"  ??"],
[0x26,"SetDataRate"			,"  ??"],
[0x27,"SecurityAccess"			,"0x89"],
[0x2D,"DynamicallyDefineLocalD"		,"  ??"],
[0x2E,"WriteDataByCommonID"		,"0x89"],
[0x2F,"InputOutputControlByCommonID"	,"  ??"],
[0x30,"InputOutputControlByLocalID"	,"0x89"],
[0x31,"StartRoutineByLocalID"		,"  ??"],
[0x32,"StopRoutineByLocalID"		,"0x89"],
[0x33,"RequestRoutineResultByLocalID"	,"  ??"],
[0x34,"RequestDownload"			,"0x89"],
[0x35,"RequestUpload"			,"0x89"],
[0x36,"TransferData"			,"0x89"],
[0x37,"RequestTransferExit"		,"0x89"],
[0x38,"StartRoutineByAddress"		,"  ??"],
[0x39,"StopRoutineByAddress"		,"  ??"],
[0x3A,"RequestRoutineResultByAddress"	,"  ??"],
[0x3B,"WriteDataByLocalIdentification"  ,"  ??"],
[0x3D,"WriteMemoryByAddress"		,"  ??"],
[0x3E,"TesterPresent"			,"0x89"],
[0x82,"??"				,"0x89"],
[0x83,"AccessTimingParameters"		,"  ??"],
[0x99,"??"				,"0x89"],
[0x1A,"ReadECUIdentification"		,"  ??"],
[0xBE,"??"				,"0x89"]
                        ]
   for ID in range (len(ListKWP2000Services)):
    if ListKWP2000Services[ID][0] == ServiceID:
     return ListKWP2000Services[ID][1]

def TP20_HandleReturn(bus,TP20_Channel,ID):
    retData = bytearray()
    FirstRecv=True 
    while True:
     recv_message = bus.recv(0.1)
     if recv_message == None:
      sleep(0.01)
     else:
      #print (recv_message)
      if len(recv_message.data) == 1: 
       if recv_message.data[0] == 0xA3:
          WorkingFrame = [0xA0,0x0F,0x8A,0xFF,0x32,0xFF]
          msg = can.Message(arbitration_id=TP20_Channel,data=WorkingFrame,is_extended_id=False)
          bus.send(msg)
       else:
        continue


      if len(recv_message.data) == 6 and recv_message.data[5] == 0x78:
       print ("Recv: 0x78 Retry ",end='')
       TP20_SendACK(bus,TP20_Channel,recv_message.data[0])
      else:
       if (recv_message.data[0]&0xF0)==0x20:
        if FirstRecv==True:
         if recv_message.data[3] == 0x67: # SecurityAccess
          retData = retData + recv_message.data[5:8]
         else:
          retData = retData + recv_message.data[6:8]
         FirstRecv=False
        else:
         retData = retData + recv_message.data[1:8]
        #print ("Recv: there is more ") #,end='')
        #TP20_SendACK(bus,TP20_Channel)

       else: # last ack 
        retData = retData + recv_message.data[1:8]
        if len(recv_message.data) >5:
         if recv_message.data[3] == 0x67 and recv_message.data[4] == 0x04:
          print ("  ... Security Access OK ret = 0x%2.2x"%(recv_message.data[5]))
         
         if (recv_message.data[3] == 0x7F) and (recv_message.data[5] != 0x11): 
          #print("")
          #print("0x%4.4x = %s %s" % (ID, str(retData),binascii.hexlify(retData)))
          print("0x%2.2x = %s %s"% ( ID,binascii.hexlify(retData),KWP2000_ServiceIdToString(ID) ))
         else:
          pass # keine Ausgabe bei Fehlern
        
         #else:
         # print("0x%2.2x = %s %s"% ( ID,binascii.hexlify(retData),KWP2000_ServiceIdToString(ID) ))

        TP20_SendACK(bus,TP20_Channel,recv_message.data[0])
        break
    return retData

def TP20_ReadDataByIdent(bus,arbitration_id,ID):
       WorkingFrame = [0x10,0x00,0x03,0x22,ID>>8,ID&0x00FF]
       TP20_Send(bus,arbitration_id,WorkingFrame)

       TP20_HandleReturn(bus,arbitration_id,ID)

def TP20_ReadMemoryByAddress(bus,arbitration_id,Addr,Size):
       #WorkingFrame = [0x10,0x00,0x07,0x23,Addr>>24,Addr>>16,Addr>>8,Addr&0x000000FF,Size>>8,Size&0x00FF] 
       #WorkingFrame = [0x10,0x00,0x07,0x23,0x12,Addr>>8,Addr&0x000000FF,Size&0x00FF] 
       for i in range (3,4):
        WorkingFrame = [0x20,0x00,0x07,0x23,0x00,0x00,0x00] #,0xFF,0x01,0x01] 
        TP20_Send(bus,arbitration_id,WorkingFrame)
        sleep(0.1) 
        WorkingFrame = [0x10,0x20,0x01,0x01,0x00,0x00,0x00]
        TP20_Send(bus,arbitration_id,WorkingFrame[0:i+1])
        TP20_HandleReturn(bus,arbitration_id,Addr)
        sleep(0.1)
        TP20_Alife(bus,arbitration_id)



def TP20_FindServices(bus,arbitration_id,DiagnosticSession=0x89):
       print("Trying Service 0x00 to 0xFF with Data [0x10,0x00,0x05,ServiceID,0x12,0x00,0x00,0x00]")
       print("Ignoring all 0x11 serviceNotSupported Error Answers") 
       print("Using Diagnostic Session %2.2x"%(DiagnosticSession))

       #MK60EC1ListOfLogins = [30204,30205,30206,30207,30208,30210,40168,31857,5641,
       #                    10149,11122,11123,40304,25004,11966,40171,24435,15081,25144,14913,30203]
       MK60EC1ListOfLogins = [11908]

       TP20_StartDiagnosticSession(bus,arbitration_id,DiagnosticSession)
       for Login in MK60EC1ListOfLogins:
        TP20_SecurityAccess(bus,arbitration_id,Login,0x03)
        sleep(0.1)
        TP20_Alife(bus,arbitration_id)

        for ServiceID in range (0x20,0x30):
         WorkingFrame = [0x10,0x00,0x05,ServiceID,0x12,0x00,0x00,0x00]
         TP20_Send(bus,arbitration_id,WorkingFrame)
         TP20_HandleReturn(bus,arbitration_id,ServiceID)
         sleep(0.01)
         continue

         for SubFunc in range (0,0x1):
          for Type in range (0,1):
           for addr16Bit in range (0,0x020,0x20): ##12345
            TP20_Alife(bus,arbitration_id)
            WorkingFrame = [0x10,0x00,0x05,ServiceID,0x12,0x00,0x00,0x00]
            #                ADD  Add Add  Type Size Size Size
            AddrHi,AddrLo = SplitToBytes(addr16Bit)
            DummyPayload = [0x00,AddrHi,AddrLo,Type,0x00,0x00,0x20]
            for i in range (7,8): #(0,12):
             if (i >4):
              j=4
              Start=0x20
             else:
              j=i
              Start=0x10

             #WorkingFrame = [Start,0x00,i+1,ServiceID] + DummyPayload[0:j] 
             ###WorkingFrame = [0x10,0x00,0x03,ServiceID,SubFunc,0x00]
             #print ("SubFunc:%2.2x "%(SubFunc),end='') 
             #print ("Length:%d "%(i),end='') 
             #print ("UploadType:%d "%(Type),end='') 
             TP20_Send(bus,arbitration_id,WorkingFrame)
             sleep(0.01)

            if(i >4): #second frame
             WorkingFrame = [0x10] + DummyPayload[4:i]
             TP20_Send(bus,arbitration_id,WorkingFrame)

            TP20_HandleReturn(bus,arbitration_id,ServiceID)
            sleep(0.01)

            #TransferData
            WorkingFrame = [0x10,0x00,0x00,0x36]
            TP20_Send(bus,arbitration_id,WorkingFrame)
            TP20_HandleReturn(bus,arbitration_id,ServiceID)
            sleep(0.01)
           
           

def TP20_RequestUpload(bus,TP20_Channel,DataPayload):
        TP20_Send(bus,TP20_Channel,[0x20,0x00,0x08,0x34,0x00,0x06,0x00,0x00])
        sleep(0.1)
        TP20_Send(bus,TP20_Channel,[0x10,0x00,0x11,0x60])
        return

        FrameNr=0
        DataToSendPtr=0
        DataSize = len(DataPayload)
        print("TP20_RequestUp DataPayload Size: " + hex(DataSize))        
        #WorkingFrame = [0x10,0x0B,0x34,0x01,0x44,0x03,0xFF,0x19]
        if DataSize > 4:
           #WorkingFrame = [0x10,0x00,DataSize+1,0x35] + DataPayload[DataToSendPtr:DataToSendPtr+4]
           WorkingFrame = [0x10,0x00,DataSize,0x35] + DataPayload[DataToSendPtr:DataToSendPtr+4]
           DataToSendPtr=DataToSendPtr+4 # 4 Bytes gesendet
        else: # =< 4 nur 1 Frame
           WorkingFrame = [0x10,0x00,0x00,0x35,0x00,0x00,0x00] #+ DataPayload[DataToSendPtr:DataToSendPtr+DataSize]
           DataToSendPtr=DataToSendPtr+4 # 4 Bytes gesendet

           #WorkingFrame = [DataSize+1,0x35] + DataPayload[DataToSendPtr:DataToSendPtr+DataSize]
           #WorkingFrame = FillUpCanFrame(WorkingFrame)

        msg = can.Message(arbitration_id=TP20_Channel,data=WorkingFrame,is_extended_id=False)
        bus.send(msg)
        recv_message = bus.recv(2.0) # 2 s Timeout        

        if DataSize > 4:
           FrameNr=FrameNr+1
           WorkingFrame = [0x10+FrameNr] +  DataPayload[DataToSendPtr:DataToSendPtr+7]
           #WorkingFrame = FillUpCanFrame(WorkingFrame)
           msg = can.Message(arbitration_id=TP20_Channel,data=WorkingFrame,is_extended_id=False)
           bus.send(msg)  
           recv_message = bus.recv(2.0) # 2 s Timeout            
        else:
          pass       

def TP20_Alife(bus,TP20_Channel):
       bus.send(can.Message(arbitration_id=TP20_Channel,data=[0xA3],is_extended_id=False))
       bus.recv(0.5)

def TP20_InitChannel(bus):
              WorkingFrame = [0x03,0xC0,0x00,0x10,0x00,0x03,0x01]
              msg = can.Message(arbitration_id=0x200,data=WorkingFrame,is_extended_id=False)
              bus.send(msg)
              while (True):
                recv_message = bus.recv(1)
                if recv_message == None:
                 sleep(0.1)
                else:
                 if recv_message.arbitration_id == 0x203:
                  TP20_Channel=recv_message.data[4]+(recv_message.data[5]<<8)
                  print ("TP20 Channel to ABS is: 0x%x" % (TP20_Channel))

                  WorkingFrame = [0xA0,0x0F,0x8A,0xFF,0x32,0xFF]
                  msg = can.Message(arbitration_id=TP20_Channel,data=WorkingFrame,is_extended_id=False)
                  bus.send(msg)
                  recv_message = bus.recv(1)
                  sleep(0.1)
                  return TP20_Channel
                 else:
                  pass

def TP20_StartDiagnosticSession(bus,TP20_Channel,SessionType):
    WorkingFrame = [0x10,0x00,0x02,0x10,SessionType]
    TP20_Send(bus,TP20_Channel,WorkingFrame)

    recv_message = bus.recv(1)
    recv_message = bus.recv(1)
    if (len(recv_message.data) > 5) and (recv_message.data[5] != 0x11):
     print(recv_message)
    else:
     pass
    if (recv_message.data[3]==0x50):
     print("DiagSession 0x%2.2x entered" %(SessionType) )

    TP20_SendACK(bus,TP20_Channel,recv_message.data[0])
    sleep(0.01)

def send_one():

    # this uses the default configuration (for example from the config file)
    # see https://python-can.readthedocs.io/en/stable/configuration.html
    #bus = can.interface.Bus()

    # Using specific buses works similar:
    with can.interface.Bus(bustype='socketcan', channel='can0', bitrate=500000) as bus, \
            can.interface.Bus(bustype='socketcan', channel='can1', bitrate=500000) as bus1:

      MK60EC1ListOfLogins = [30204,30205,30206,30207,30208,30210,40168,31857,5641,
                           10149,11122,11123,40304,25004,11966,40171,24435,15081,25144,14913,30203]

      try:
        if len(sys.argv) > 1:
            print (sys.argv[1])

            if (sys.argv[1]) == "-TP20_StartDiagnosticSession":
             Session = int(sys.argv[2],16)
             TP20_Channel = TP20_InitChannel(bus)
             TP20_StartDiagnosticSession(bus,TP20_Channel,Session)
             sys.exit(0)

            if (sys.argv[1]) == "-TP20_SecurityAccess":
             Magic = int(sys.argv[2],10)
             Type= int(sys.argv[3],10)
             Session = int(sys.argv[4],16)
             TP20_Channel = TP20_InitChannel(bus)
             sleep(0.1)
             TP20_StartDiagnosticSession(bus,TP20_Channel,Session)
             if Magic==0:
              #for Login in MK60EC1ListOfLogins:
              for Login in range (0,0xFFFF):
               TP20_SecurityAccess(bus,TP20_Channel,Login)
               TP20_Alife(bus,TP20_Channel)
             else:
              TP20_SecurityAccess(bus,TP20_Channel,Magic,Type)
             sys.exit(0)

            if (sys.argv[1]) == "-TP20_FindServices":
             DiagnosticSession = int(sys.argv[2],16)
             TP20_Channel = TP20_InitChannel(bus)
             #TP20_StartDiagnosticSession(bus,TP20_Channel,0x83)
             TP20_FindServices(bus,TP20_Channel,DiagnosticSession)
             sys.exit(0)

            if (sys.argv[1]) == "-TP20_ReadMemoryByAddress":
             TP20_Channel = TP20_InitChannel(bus)
             TP20_StartDiagnosticSession(bus,TP20_Channel,0x83)
             #MK60EC1ListOfLogins = [30204,30205,30206,30207,30208,30210,40168,31857,5641,
             #                       10149,11122,11123,40304,25004,11966,40171,24435,15081,25144,14913,30203] 
             MK60EC1ListOfLogins = [11908]
             for Login in MK60EC1ListOfLogins:
              TP20_SecurityAccess(bus,TP20_Channel,Login)
              TP20_ReadMemoryByAddress(bus,TP20_Channel,0xFFFFFF,0x20)
             sys.exit(0)

            if (sys.argv[1]) == "-TP20_FindDiagnosticSession":
             TP20_Channel = TP20_InitChannel(bus)
             for Login in MK60EC1ListOfLogins:
              TP20_SecurityAccess(bus,TP20_Channel,Login)
              for i in range (0x00,0x85):
              #for i in range (0x80,0x89):
               #print("ID: 0x%2.2x " %(i),end='')
               TP20_StartDiagnosticSession(bus,TP20_Channel,i)
               TP20_Alife(bus,TP20_Channel)
             sys.exit(0)

            if (sys.argv[1]) == "-TP20_RequestUpload":
             TP20_Channel = TP20_InitChannel(bus)
             #TP20_RequestUpload(bus,TP20_Channel,[0x02,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00])
             TP20_RequestUpload(bus,TP20_Channel,[0xFF])
             sys.exit(0)

            if (sys.argv[1]) == "-TP20_readDataByCommonIdentifier":
             CommonIdentifier = int(sys.argv[2],16)
             DiagnosticSession = int(sys.argv[3],16)
             Login = int(sys.argv[4],10)
             TP20_Channel = TP20_InitChannel(bus)
             TP20_StartDiagnosticSession(bus,TP20_Channel,DiagnosticSession)
             TP20_SecurityAccess(bus,TP20_Channel,Login,3)
             TP20_ReadDataByIdent(bus,TP20_Channel,CommonIdentifier)
             TP20_Alife(bus,TP20_Channel)
             sys.exit(0)
            
            if (sys.argv[1]) == "-CCP":

                for CanIds in range(0x6A2,0x6A3):
                 StationIDHigh=0x00
                 #StationIDLow=0x00
                 for StationIDLow in range(0x00,0x100):
                  for StationIDHigh in range(0x00,0x100):
                   WorkingFrame = [0x01,0x00,StationIDLow,StationIDHigh,0x00,0x00,0x00,0x00] 
                   msg = can.Message(arbitration_id=CanIds,data=WorkingFrame,is_extended_id=False)
                   bus.send(msg)
                   sleep(0.01)

                sys.exit(0) 

            if (sys.argv[1]) == "-TP20":

                WorkingFrame = [0x03,0xC0,0x00,0x10,0x00,0x03,0x01]
                msg = can.Message(arbitration_id=0x200,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                recv_message = bus.recv(1)
                if recv_message == None:
                 sleep(0.1)
                else:
                 print (recv_message.data)
                 TP20_Channel=recv_message.data[4]+(recv_message.data[5]<<8)
                 print ("Channel to ABS is: 0x%x" % (TP20_Channel))


                 WorkingFrame = [0xA0,0x0F,0x8A,0xFF,0x32,0xFF]
                 msg = can.Message(arbitration_id=TP20_Channel,data=WorkingFrame,is_extended_id=False)
                 bus.send(msg)
                 recv_message = bus.recv(1)

                 WorkingFrame = [0x10,0x00,0x02,0x10,0x89]
                 TP20_Send(bus,TP20_Channel,WorkingFrame)

                 recv_message = bus.recv(1)
                 recv_message = bus.recv(1)

                 TP20_SendACK(bus,TP20_Channel)
                 sleep(0.5)
                 WorkingFrame = [0x10,0x00,0x02,0x1A,0x9B]
                 TP20_Send(bus,TP20_Channel,WorkingFrame)

                 TP20_HandleReturn(bus,TP20_Channel,0x00)

                 sleep(0.01)
                 TP20_ReadDataByIdent(bus,TP20_Channel,0xF19E)
                 #sleep(0.01)
                 #TP20_ReadDataByIdent(bus,TP20_Channel,0xF18C)
                 #sleep(0.01)
                 #TP20_ReadDataByIdent(bus,TP20_Channel,0xF17C)
                 #sleep(0.01)
                 #TP20_ReadDataByIdent(bus,TP20_Channel,0xF17C)
                 #sleep(0.01)

                 TP20_FindServices(bus,TP20_Channel)

                 #for i in range (0,0x100):
                 # TP20_Alife(bus,TP20_Channel)
                 # TP20_ReadMemoryByAddress(bus,TP20_Channel,0x00,0x20,i)
                 # sleep(0.01)

                 #sys.exit(0)

                 TP20_ReadDataByIdent(bus,TP20_Channel,0xF17E)
                 sleep(0.01)

                 bus.send(can.Message(arbitration_id=TP20_Channel,data=[0xA3],is_extended_id=False))
                 bus.recv(0.5)

                 TP20_ReadDataByIdent(bus,TP20_Channel,0xF17E)
                 sleep(0.01)

                 #for i in range (0x1000,0xFFFF):
                 for i in range (0x000,0xFFF):
                  bus.send(can.Message(arbitration_id=TP20_Channel,data=[0xA3],is_extended_id=False))
                  bus.recv(0.5)
                  TP20_ReadDataByIdent(bus,TP20_Channel,i)
                  sleep(0.01)

                  #bus.send(can.Message(arbitration_id=TP20_Channel,data=[0xA3],is_extended_id=False))
                  #bus.recv(0.5)
                  #sleep(1.5)

                 sys.exit(0)

                 TP20_ReadDataByIdent(bus,TP20_Channel,0xF187)
                 #msg = can.Message(arbitration_id=TP20_Channel,data=[0xA3],is_extended_id=False)
                 #bus.send(msg)
                 bus.recv(1.5) # wait for A3 ACK to go on
                 sleep(1.5)
                 TP20_ReadDataByIdent(bus,TP20_Channel,0xF188)
                 #bus.recv(1.5)
                 sleep(1.5)
                 TP20_ReadDataByIdent(bus,TP20_Channel,0xF189)


                 #WorkingFrame = [0x10,0x00,0x03,0x22,0xF1,0x87]
                 #TP20_Send(bus,TP20_Channel,WorkingFrame)

                 #TP20_HandleReturn(bus,TP20_Channel)

                sys.exit(0)


            if (sys.argv[1]) == "-7N0FTSHold":
             print("7N0FTSHold")
             mACC_SystemCounter = 0
             State = 0
             StoppingCounter = 0
             while True:
              recv_message = bus.recv(0.01)
              if recv_message == None:
               sleep(0.1)
              else:

               if recv_message.arbitration_id == 0x366: 
                bus1.send(can.Message(arbitration_id=0x366,data=recv_message.data,is_extended_id=False))
                sleep(0.001)
               if recv_message.arbitration_id == 0x56A:
                bus1.send(can.Message(arbitration_id=0x56A,data=recv_message.data,is_extended_id=False))
                sleep(0.001)
               if recv_message.arbitration_id == 0x674:
                bus1.send(can.Message(arbitration_id=0x674,data=recv_message.data,is_extended_id=False))
                sleep(0.001)

               if recv_message.arbitration_id == 0x368: #mACC_System
                mACC_SystemCounter = mACC_SystemCounter + 1
                #print("Orig     : %2.2x %2.2x %2.2x %2.2x %2.2x %2.2x %2.2x %2.2x" % (recv_message.data[0], recv_message.data[1],recv_message.data[2],recv_message.data[3],recv_message.data[4],recv_message.data[5],recv_message.data[6],recv_message.data[7] ))
                if recv_message.data[4] & 1 << 6 == 0x40: # ACC Bremst
                 State = 1

                if State == 1:
                 recv_message.data[4] = recv_message.data[4] | 1 << 6
                 StoppingCounter = StoppingCounter + 1
                 if StoppingCounter == 5000:
                  State = 0

                #print("Patched  : %2.2x %2.2x %2.2x %2.2x %2.2x %2.2x %2.2x %2.2x" % (recv_message.data[0], recv_message.data[1],recv_message.data[2],recv_message.data[3],recv_message.data[4],recv_message.data[5],recv_message.data[6],recv_message.data[7]))
                
                CheckSum = 0x00
                for Byte in recv_message.data[1:8]:
                 #print("Byte: %2.2x CheckSum %2.2x"%(Byte,CheckSum))
                 CheckSum = CheckSum ^ Byte
                 recv_message.data[0] = CheckSum
                #print("CrcUpdate: %2.2x %2.2x %2.2x %2.2x %2.2x %2.2x %2.2x %2.2x" % (recv_message.data[0], recv_message.data[1],recv_message.data[2],recv_message.data[3],recv_message.data[4],recv_message.data[5],recv_message.data[6],recv_message.data[7]))
                #print("<== new")

                #sleep(0.5)
                bus1.send(can.Message(arbitration_id=0x368,data=recv_message.data,is_extended_id=False))
                #if (mACC_SystemCounter == 1000):
                # print(" " + str(mACC_SystemCounter),end='')
                # mACC_SystemCounter = 0
                #else:
                sleep(0.001)


            if (sys.argv[1]) == "-TachoMenuTest":
             i=0x0c
             u=0x20
             switch = True
             while (True):
                sleep(1)

                bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('0C42030031000301', 'hex'),is_extended_id=False))
                recv_message = bus1.recv(1.0)
                bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('802D4C4103003100', 'hex'),is_extended_id=False))
                recv_message = bus1.recv(1.0)
                bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('C0030108003803FF', 'hex'),is_extended_id=False))
                recv_message = bus1.recv(1.0)
                bus1.send(can.Message(arbitration_id=0x66C,data=codecs.decode('4C4F00', 'hex'),is_extended_id=False))
                recv_message = bus1.recv(1.0)


                astr= "%2.2x" % (u)
                print (switch)
                switch = not switch
                MenuTacho(bus1,i,u,switch)
                #i=i+1
                #if i>10: i=0
                #u=u+1
                #if u>255:u=0

            if (sys.argv[1]) == "-EPB":    
                 Addr = 0x13A0
                 TmpData = UDS_ReadMemoryByAddress(bus,0x752,0x04,0x00,Addr,0x10)
                 #print(TmpData,end='')
                 print( " "+str(str(hex(Addr)))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )
                 boolQuiet = True
                 for ID in range (0x0,0xFFFF):
                  TmpData = UDS_ReadDataByIdentifier(bus,0x752,ID)
                  #print("ABS VIN: " +str(codecs.encode( bytearray(TmpData[2:8]) ,'hex') ))
                  #print (TmpData)
                  del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
                  #del TmpData[0:3] # drei bytes crap aus den Antwort Daten entfernen
                  #del TmpData[7:9] # crap am Ende entfernen 
                  if not TmpData == []:
                   print(TmpData,end= '\n')

                 sys.exit(0)   


            if  (sys.argv[1]) == "-TachoTest":
              print("TachoTest 1 2 3")
              speedLow = 0x00
              speedHigh = 100
              while (True):
                #bus1.send(can.Message(arbitration_id=0x3D0,data=[0x00, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],is_extended_id=False))
                #recv_message = bus1.recv(2.0)
                #bus1.send(can.Message(arbitration_id=0xDA0,data=[0x01, 0x80, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00],is_extended_id=False))
                #recv_message = bus1.recv(2.0)
                #bus1.send(can.Message(arbitration_id=0x531,data=[0x14, 0x80, 0x03],is_extended_id=False))
                #recv_message = bus1.recv(2.0)
                #bus1.send(can.Message(arbitration_id=0x470,data=[0x00, 0x3F, 0x00, 0x00, 0x02, 0xFF, 0x02, 0x00],is_extended_id=False))
                #recv_message = bus1.recv(2.0)
                #Airbag
                bus1.send(can.Message(arbitration_id=0x50,data=[0x00, 0x80, 0x04, 0x00, 0x00, 0x00, 0x00, 0x00],is_extended_id=False))
                recv_message = bus1.recv(2.0)
                #ABS
                absLampen=0x00
                #bus1.send(can.Message(arbitration_id=0x5A0,data=[0x18, speedLow, speedHigh, absLampen, 0xFE, 0xFE, 0x00, 0xFF],is_extended_id=False))
                #recv_message = bus1.recv(2.0)
                bus1.send(can.Message(arbitration_id=0x1A0,data=[0x18, speedLow, speedHigh, absLampen, 0xFE, 0xFE, 0x00, 0xFF],is_extended_id=False))
                recv_message = bus1.recv(2.0)
                #Coolant Temp |  GRA light 
                #WATER_TEMP = 50
                #water_temp_data = 0xb8 #+ (WATER_TEMP * 15);
                #gra_status_light_data = 0x80
                #bus1.send(can.Message(arbitration_id=0x288,data=[0x00, water_temp_data, gra_status_light_data, 0x00, 0x00, 0x00, 0x00, 0x00],is_extended_id=False))
                #recv_message = bus1.recv(2.0)


                print("sending ...")
                sleep(0.2)


            if (sys.argv[1]) == "-ABSStatus":
                while (True):
                 TmpData = UDS_ReadDataByIdentifier(bus,0x713,0x1820)
                 #print("ABS VIN: " +str(codecs.encode( bytearray(TmpData[2:8]) ,'hex') ))
                 #print (TmpData)
                 del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
                 del TmpData[0:3] # drei bytes crap aus den Antwort Daten entfernen
                 del TmpData[7:9] # crap am Ende entfernen 
                 print(TmpData,end= '\n')
                 #print( str( codecs.encode( bytearray(TmpData) ,'hex') ) )

                 sleep(5)
                 return

            if (sys.argv[1]) == "-CPSimulator":
               for id in range (0x100,0x7FF):
                bus1.send(can.Message(arbitration_id=id,data=codecs.decode('100b8001D3114183', 'hex'),is_extended_id=False))
                #id=0x757
                for i in range (0,20):
                 recv_message = bus1.recv(1.0) # 2 s Timeout
                 if recv_message == None:
                  return ["Timeout"]
                 if recv_message.data[0] == 0x30:
                  print("\n\n")
                  print(str(hex(id)))
                
                sleep(0.05)
                #bus1.send(can.Message(arbitration_id=id,data=codecs.decode('21F4CFDF0600AAAA', 'hex'),is_extended_id=False))
                #sleep(0.5)
               
               return

            if (sys.argv[1]) == "-ACC_ShowAllids":     
                for i in range (0,0x10000): #[0xf17c,0xf187,0xf189,0xf191,0xf195,0xf197,0xf19e,0xf1a0]: #range(0,0x10000):
                 Data = UDS_ReadDataByIdentifier(bus,0x757,i)
                 if Data != []:
                  #print(str(bytearray(Data[2:]),'utf-8'))
                  print(" "+ str(codecs.encode( bytearray(Data[2:]) ,'hex') )+" "+  str(bytearray(Data[2:])))
                return


            if (sys.argv[1]) == "-DakuTest":
             #for i in range (0x70c,0x70d):
             #bus.send(can.Message(arbitration_id=0x745,data=codecs.decode('0210035555555555', 'hex'),is_extended_id=False))
             #sleep(1)

             bus1.send(can.Message(arbitration_id=0x66F,data=codecs.decode('0890484A00030000', 'hex'),is_extended_id=False))

             #bus1.send(can.Message(arbitration_id=0x280,data=codecs.decode('0800000000000000', 'hex'),is_extended_id=False))
             return

            if (sys.argv[1]) == "-VCRN_Hack":
             bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('0111555555555555', 'hex'),is_extended_id=False))
             while(1): 
              recv_message = bus.recv(1.0) # 1 s Timeout
              if recv_message == None:
                continue
              if recv_message.data[0] == 0x03 and recv_message.data[1] == 0x6E and recv_message.data[2] == 0x00 and recv_message.data[3] == 0xBE:
                  print("0x00BE")
                  while(1):
                   bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('0111555555555555', 'hex'),is_extended_id=False))
                   sleep(0.001)

             return

            if (sys.argv[1]) == "-VCRN_Hack2":
                  while(1):
                   bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('0111555555555555', 'hex'),is_extended_id=False))
                   sleep(0.001)


            if (sys.argv[1]) == "-3QFSwap":
             SwapData = list(codecs.decode(sys.argv[2], 'hex'))

             for i in [0xf187,0xf189,0xf191,0xf195,0xf197,0xf19e]: 
              Data = UDS_ReadDataByIdentifier(bus,0x757,i)
              if Data != []:
               print(str(bytearray(Data[2:]),'utf-8'))

             bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('0210035555555555', 'hex'),is_extended_id=False))
             UDS_Receive(bus,0x757)

             # ???
             UDS_WriteDataByIdentifier(bus,0x757,0xF198,[0x00,0x00,0x00,0x00,0x00,0x2E])
             # Datum muss dem des Swaps entsprchen !
             UDS_WriteDataByIdentifier(bus,0x757,0xF199,[0x21, 0x11, 0x20])

             print("Enter Diagnostic Session Control VW EOL")
             bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('0210405555555555', 'hex'),is_extended_id=False))
             for i in range (0,20):
              recv_message = bus.recv(1.0) # 1 s Timeout
              if recv_message == None:
                 return ["Timeout"]
              if recv_message.data[0] == 0x06 and recv_message.data[1] == 0x50 and recv_message.data[2] == 0x40:
                  print("OK Enter Diagnostic Session Control VW EOL")
                  break 

             UDS_SecurityAccess(bus,0x757,20103)

             TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x3C01)
             #del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
             print(str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))

             UDS_WriteDataByIdentifier(bus,0x757,0x3C01,SwapData)

             TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x3C01)
             #del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
             #print(str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))

             WorkingFrame = [0x04,0x31,0x03,0xC0,0x01]
             WorkingFrame = FillUpCanFrame(WorkingFrame)
             msg = can.Message(arbitration_id=0x757,data=WorkingFrame,is_extended_id=False)

             for i in range (0,5):
              bus.send(msg)        
              Status = UDS_Receive(bus,0x757)
              print(str(codecs.encode( bytearray(Status) ,'hex') ))
              sleep(1)

             bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('043101c001555555', 'hex'),is_extended_id=False))
             UDS_Receive(bus,0x757)

             for i in range (0,15):
              bus.send(msg)        
              Status = UDS_Receive(bus,0x757)
              print(str(codecs.encode( bytearray(Status) ,'hex') ))
              if Status[3] == 0x02 and Status[4] == 0xFF:
                print ("Ready")
                return
              sleep(1)

             bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('043102c001555555', 'hex'),is_extended_id=False))
             UDS_Receive(bus,0x757)

             return

            if (sys.argv[1]) == "-3QFSwap2":
             SwapData = list(codecs.decode(sys.argv[2], 'hex'))

             for i in [0xf187,0xf189,0xf191,0xf195,0xf197,0xf19e]: 
              Data = UDS_ReadDataByIdentifier(bus,0x757,i)
              if Data != []:
               print(str(bytearray(Data[2:]),'utf-8'))

             #Set DiagSession
             bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('0210035555555555', 'hex'),is_extended_id=False))
             UDS_Receive(bus,0x757)

             # ???
             UDS_WriteDataByIdentifier(bus,0x757,0xF198,[0xFF,0xFF,0xFF,0xFF,0xFF,0xFF])
             # Datum muss dem des Swaps entsprchen !
             UDS_WriteDataByIdentifier(bus,0x757,0xF199,[0x21, 0x11, 0x27])

             print("Enter Diagnostic Session Control VW EOL")
             bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('0210405555555555', 'hex'),is_extended_id=False))
             for i in range (0,20):
              recv_message = bus.recv(1.0) # 1 s Timeout
              if recv_message == None:
                 return ["Timeout"]
              if recv_message.data[0] == 0x06 and recv_message.data[1] == 0x50 and recv_message.data[2] == 0x40:
                  print("OK Enter Diagnostic Session Control VW EOL")
                  break 

             UDS_SecurityAccess(bus,0x757,20103)

             #Löschen einer SWaP Funktion
             #bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('10083101C002FFFF', 'hex'),is_extended_id=False))
             #UDS_Receive(bus,0x757)
             #bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('21FFFA5555555555', 'hex'),is_extended_id=False))
             #UDS_Receive(bus,0x757)

             #return

             UDS_WriteDataByIdentifier(bus,0x757,0x3C01,SwapData)

             bus.send(can.Message(arbitration_id=0x757,data=codecs.decode('043101C001555555', 'hex'),is_extended_id=False))
             UDS_Receive(bus,0x757)

             WorkingFrame = [0x04,0x31,0x03,0xC0,0x01]
             WorkingFrame = FillUpCanFrame(WorkingFrame)
             msg = can.Message(arbitration_id=0x757,data=WorkingFrame,is_extended_id=False)

             #return:
             #  can0  7C1   [8]  07 71 03 C0 01 02 00 05   '.q......' ==> falsches datum
             #                                     00 03              ==> falsche Signatur
             for i in range (0,10):
              bus.send(msg)        
              Status = UDS_Receive(bus,0x757)
              print(str(codecs.encode( bytearray(Status) ,'hex') ))
              if Status[3] == 0x02 and Status[4] == 0xFF:
                print ("Ready")
                return
              sleep(1)

             return

            if (sys.argv[1]) == "-ACCStatus":
                TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x03DE)
                print("Acc CP Error Counter: " +str(codecs.encode( bytearray(TmpData[2:4]) ,'hex') ))
                TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x3C0A)
                print("Acc CP VCRN: " +str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))
                TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x3C05)
                print("Acc Pub Key: " +str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))
                TmpData = UDS_ReadDataByIdentifier(bus,0x757,0xF190)
                print("Acc VINHex: " +str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))
                print("Acc VIN   : " +str(bytearray(TmpData[2:]) ,'utf-8') )
                TmpData = UDS_ReadDataByIdentifier(bus,0x757,0xF17C)
                print("Acc Serial: " +str(bytearray(TmpData[2:]) ,'utf-8') )

               	#TmpData = UDS_ReadDataByIdentifier(bus,0x773,0x03DE)
                #print("DM CP Error Counter: " +str(codecs.encode( bytearray(TmpData[2:4]) ,'hex') ))

                #TmpData = UDS_ReadDataByIdentifier(bus,0x773,0x3C0A)
                #print("DM CP VCRN: " +str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))

                TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x3C00)
                print("Acc FEC: " +str(codecs.encode( bytearray(TmpData[2:]) ,'hex') ))
                print("ACC FEC1: " +str(codecs.encode( bytearray(TmpData[2:7]) ,'hex') ))
                print("ACC FEC2: " +str(codecs.encode( bytearray(TmpData[7:12]) ,'hex') ))
                print("ACC FEC3: " +str(codecs.encode( bytearray(TmpData[12:17]) ,'hex') ))
                print("ACC FEC4: " +str(codecs.encode( bytearray(TmpData[17:22]) ,'hex') ))
                print("ACC FEC5: " +str(codecs.encode( bytearray(TmpData[22:27]) ,'hex') ))

                #TmpData = UDS_ReadDataByIdentifier(bus,0x714,0x0956)
                #print("KI CP Status (08 und 06 is OK): " +str(codecs.encode( bytearray(TmpData[2:4]) ,'hex') ))

                #Addr=0x0438
                #TmpData = UDS_ReadDataByIdentifier(bus,0x714,Addr)
                #print("KI CP Key vorhanden        " +str(codecs.encode( bytearray(TmpData[2:6]) ,'hex') ))

                #Addr=0x043A
                #TmpData = UDS_ReadDataByIdentifier(bus,0x714,Addr)
                #print("KI CP Error mit Teilnehmer " +str(codecs.encode( bytearray(TmpData[2:6]) ,'hex') ))


                return
 
            if (sys.argv[1]) == "-WriteACCSwap":
                SwapData = list(codecs.decode(sys.argv[2], 'hex'))
                UDS_WriteDataByIdentifier(bus,0x757,0x3C01,SwapData)
                return

            if (sys.argv[1]) == "-CPSniff":
                while True:
                    recv_message = bus1.recv(30.0) # 2 s Timeout
                    if(recv_message.arbitration_id==0x3DB):
                        print (recv_message)
                        
            if (sys.argv[1]) == "-CPSimu":
                bus1.send(can.Message(arbitration_id=0x3DB,data=[0x10, 0x0B, 0x80, 0x01, 0x00, 0x01, 0x02, 0x03],is_extended_id=False))
                while True:
                    recv_message = bus1.recv(2.0)
                    if recv_message.arbitration_id ==0x3EB:
                        break
                print (recv_message)
                bus1.send(can.Message(arbitration_id=0x3DB,data=[0x21, 0x04, 0x05, 0x06, 0x07, 0x00, 0xAA, 0xAA],is_extended_id=False))
                while True:
                    recv_message = bus1.recv(2.0)
                    if recv_message.arbitration_id ==0x3EB:
                        break
                print (recv_message)
                bus1.send(can.Message(arbitration_id=0x3DB,data=[0x30, 0x0F, 0x05, 0xAA, 0xAA, 0xAA, 0xAA, 0xAA],is_extended_id=False))
                while True:
                    recv_message = bus1.recv(2.0)
                    if recv_message.arbitration_id ==0x3EB:
                        break
                print (recv_message)
                return
            
            if (sys.argv[1]) == "-FindCanIds":
                for CanID in range (0x700,0x7FF):
                    #print("ID 0x%3.3x " % (CanID),end='')
                    UDS_TesterPresent(bus,CanID) 
                return
            
            if (sys.argv[1]) == "-SA2":
                TachoReset2020(bus, 0x714)
                sleep(2)

                UDS_DiagnosticSessionControl(bus, 0x714, 0x60)
                UDS_RoutineControl(bus, 0x714)
                UDS_DiagnosticSessionControl(bus, 0x714, 0x02)

                UDS_SecurityAccess_SA2(bus, 0x714)
                sys.exit(0)
            
            if (sys.argv[1]) == "-TEST":   
                print("2021.01")
                UDS_DiagnosticSessionControl(bus,0x714,0x60)
                #RESET tacho
                recv_message = UDS_WriteDataByIdentifier(bus,0x714,0xFD00,[0x01])
                sleep(7)
                
                UDS_DiagnosticSessionControl(bus,0x714,0x60)
                UDS_RoutineControl(bus,0x714)
                
                UDS_DiagnosticSessionControl(bus,0x714,0x03)
                
                UDS_DiagnosticSessionControl(bus,0x714,0x02)

                print("Bootloader Entered, LCD should be blank now")
                
                UDS_SecurityAccess_SA2(bus,0x714)

                for Identifier in [0xF187,0xf189,0xf191]: #range(0x00,0x10000):
                 TmpData = UDS_ReadDataByIdentifier(bus,0x714,Identifier)
                 del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
                 if TmpData != []:
                  print(TmpData,end='')
                  print( str( codecs.encode( bytearray(TmpData) ,'hex') ) )

                #sys.exit(0)
                #UDS_RequestUpload(bus,0x714,[0x01,0x44,0x03,0xFF,0x20,0x78,0x00,0x00,0x00,0x70]) # wird vom bootloader nicht unterstuetzt

                # 0xF15A Set Flash Tool Values, Datum und Werkstatt Code
                UDS_WriteDataByIdentifier(bus,0x714,0xF15A,[0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,0x99])

                # --- ???
                #UDS_WriteDataByIdentifier(bus,0x714,0x0410,[0x00])

                UDS_RequestDownload(bus,0x714,[0x01,0x44,0x03,0xFF,0x19,0x00,0x00,0x00,0x10,0xFF])

                DataPayloadhex = '5F5EB0B1767E666E161E060E363E262ED6DEC6CEF6FEE6EE969E868EB6BEA6AE575F474F777F676F171F070F373F272FD7DFC7CFF7FFE7EF17C8838F97899BB6126ABB4FD22D1B6C344AC4157E6ADB2FF48204D5BFA21BEF5181A4DA74A5EEFAAA5E6513B5642E33EA1EB018156BE5349F8B3ACED5A36FF6DEC37A8E10B085FBDE41081C8D794234943A4954CD39B72FB48DC3CA58A385B5939AFD8A98BCA3A8525B3C4B33759C68721C1A127335DC2892DCDFD2B3F51CE8D29CB792CCBBA3ABB50F0048504EC068F63720084F38C607F0D8BFC8A8E2834F9198E327B5B8880871F7E44936D66169575E0109779E2129979EC1C9D25EE0E9B2368489F9A3DEA97021A68EC9BEA0F9D6DEB9CEF0A9E6EE691E0510C6C14539575E2561737E05999E9FE470BABF8458C6DFE79937C06710131F18F1313F4D2F7448464F5450626FB76B8D8C9743A9ACD7C2D4CC8BFCBCF677E3010C57D3252CEBA32CB37E94445A4165A5B36545AFEF6A22A932E8CD5A1275E2253BCA3D9AD2DFA266A2747D4692979ACA90CDBAE29D102282CD3102C2FC201A421DE8C2A24D89A2CE2C007A220D496303DC684329FD21DB839C2903E3ACC9E3CB35133B242DB3A4E1B6536D116BD08F5A7090AE92A890CF1A30B0FF3A106F18581253C7252833B74148CF8784969B71A1BF654181970121E18F71F95E16F7E7211F1139613E8AA1617FF179DE965E2186C92D06FBDE29614070B68C1951A4A065A1777E4591131E4E14493E7A34B420C6CFB79918EC1BF89A9657DE05A21701B84CFC2052767645CD0A1769D92F51C9C2CAF6032EE92B63827351B9A2AA55A39E49CB831A93144EB1098BC392D2F622C4CDB1E79AED95DFC58A6245C5AA9BA5054AAF85256AFDE5450AEEC5051B3422E2F422025DEDDC64828A92DCA253DE05434A507C6673ED191C6230CAE9741CDB8F94F3FB93BBF3CCC372C2F3C3E411A2310B133C43926023633411C2571BB0EF84318598808FD661F6D0D0E784512708201F56811820505701F149782DD8919EC1308EF9B5F3F2668889D25EA4A932B64049911E2090331F0510CE3A3F4115EF876BD76064D6D603A7185686E53B77D0A47634F347E89226438B17C0A0169322E63913C7A01AB63961B7F11AC65997670EBA3689A757D63C4FFAFB0EE4DC95E21B0C3FD5B5C7556FC5B2617CAF7B6A62988B2B4F3FA0D7DBC5326FA0C5FB3C2F243A2A0FC101495AECBEB679796A336E1E81B6BA59526E91E4DAD8D2C4DA3135862E2E3D80D9D14E5E4DD189B1668E9D227911B6BEAD732931CEEEFD7C19D01F1F0CAFC8E827505CBCB4EB77606C6C6468A792AC8084F2ECDAE447FFE308E43C2137117F411611A0610FCF79012ED360E19E9140C1AEF320A1F6B500C1FFAF18601F76C1401F74A1204F5681403691610BDFB1B880E6D0210A9E3FF8ABBF575FCE08767FEF29271F4E48373F3B7FF438C2CFD410E6EFB4608E8FFBA5D8AF024425B17F7E0589131E65E1373EA6C1D2DE862809FDDA098F87666F7CBB1951B5A0A0482883656D2AE3190D493D06CAD0DDE622F4FDC6129C9DC997CABDA3955D6E440E7436DB6BAEE3083E3406246ED4967BCB5A03B0F6F7638D8CD75BA1AC30B4424B7593648B332D210B33012369D3917C347D04E1F9D3957C88F2ACBFB21254BD49139543735214FD0953DD0733328B28CFF3E8A2E46D99C39D86A3814D545962A67079429618194D134E397D33B226C0C9FFCBE1D391DB81C30E46E556310AFA4D502E786833E7010874225F28D7C8C880F6C0E2A8B0AEA0880FBF8457C385E470BEBFA4BD97D138CC9410E2EF56081B167731D82C3668765670977A5FD690798DD7F98BB7DEE6C58E490122113579070E7630D92D8B3F192C17194F77B6628C8D9652A0AD99C7BACDADE78612101D66E2343D23C5521D5875764FDA92366364DD2EA9E4EA2BDFEC8BDDE5F9D4172E04468BC388D2B40DAE49756E24626C98C29C87A28044D2DBE034F6FBABF16C1B5B1150C4262B30B4424B7593642B8FA284B80D45FE55328B58DFB2BC1DE93A5D2B132F0224185210FDB51484823B7B9C809BF1B75EAA90CEF5D0D216E0E932E6040979235E2959114709754BDE6ED266D892D347A5A8B337C1C8F610E7A80D20083A8FC72CD7B009DA5D303E9F6BFF98EED6EAC7EFDD97D53870A14147FEBD5A465D3771986C5608331614D0262FF521C3CEBEE499EE95806E71A88EA55E5DA34F9B71A3638B15F300FE7630D92D94DAF1D4D5CB0D152A623B777FE325AD5E5BC5B2F7185E6B0904FA0E150BF1D5F4E21434FEBE5B13FA66A4BA5D441B53CAA68E726B7C6324DE499F1B353C2DC4B2C9018690E969D6D3DD7C889BFC8EB213BDBC484F344A722FFD2B12DA7AA0066D250A31CECDE3EAD2A47D89F388DE9D535A65755F6364BA115ABDF504C428C231300BE4D29EE0E9ADC68089F18F5EAA4B618A287D3F9E966D5E0009170E1030D0927F37CE05EA0070710A9575ADA1BA0B4F4048F56D027AFA3D4036CF3B213A430708001F0F09391816B74350374D7992A27D65985E57A03DC593C7F8F07DF5421609013037D9DEEB542D7BB374498F82917C84995FB3A1BBEB73C4D91FF5E1A5ED22F95BD8C8155A520A4C85712B55AE8B94B2B942A277DC0FD792F00FEE0719FE0DF3382D332324536B7584736B599BD18BC904B4075FFBE535C3FBC9EBA11C5EB303A2C82C2458545D46F574650468F3CC8686B210DADCD4CA2CF0A436B5375A04053AFD21FD8734E4ACF1427E6580ADEEC2BCB5B4E55D2ABFC5F7150DB4DC132E504C36AB13848FD5516D766C6021695C83BCB010595CC36BE3DDB1EFE60227163F1631E36FA054CFB8AB548F36058AAF61CDB74AB25F281BE0E2C7CCA059505178BF704166D458F703B8CFCE05388172C5D8169AE0186F3CA70DB588467B515511F3714E631D112807F97D2921B8D189CF06F2C886B8B6AB87131BFCF436454B4258747262E5ED6B151B156A2C252DABF5E3F2CAF4CF92CA959E4DEAB579ACCE4673737A6178240E033CEB2A5198A4C8C3F31BD4E5E5B27480C0B3AB415C464E24A115E03B1D144D16F7D5B024DED23C3B0501ECF67C75368121A3ADA45FB57243D754926666151113C2CA47376ED04DC2A7F4AFE59695C985EBB5C3A52956C846D876C4669716AE065F362EEC2BFBF1C024D711E5E596B391B3B68E709757F6567D715798AE120DD7E5372F353ADAF2A0FAF7CCD09A978DD766D663F612DF89807A81E9B29E9FC8C002E14915252701001B772D2042685308A141E89F39B369D073B4EAF6DAD15CB42338D4DE1411EEC8E05C8A165A51A970C3BCEC0C9A804F8F87E5AFA2E7B5C3C238A360A51B12C8637B2066655A52777D77728D733A666ED6868CA2A3C093CCF36BC12CE39BECCD22DB62D966EE1E7654727370235EDA737BBE843C96D5EC4C3BA2D50CB5BE29E93901032924616B45445A436D647AA46FB028B890F2D8D5F09AF4F5C7B21C15E654E718106A5055840B8275A92F577F6BA38381A7A66BCB4E390ED6F03454C78EF98C16E4305F564C975870D1996093D5B6A4F7AF9D5F28F7E7F5276F18A308EFD6BD3AEA2A7951838B2A22D098EC2E2DC5F812ABE79B902D85B85215FF595063102527696005FE1800D8D19A2566D69F3F5AB6EAE191C103819EB3A1A151534F99398F9662864E3C2606CF1D06E135CBC2FD1AE1E46A6D3BAF87A5ABA27A1C5A42D13BE362F303B307387AA322DBC14ED664C4EAE399CB57DA30E4AAA35D6B0C7D84702A515C44332464042B239DC625D57D01ACEA6397ED83959391C35D544554A06517731D14A56541532D244282CCC5F7F31D1A7FC28D85A3B7A5A54E5745ADE0756B851ACD8DFA0936D9729ED4C4D6B4A0EEE614D141F8B6B01159844B0C507E764C51DB68153E3D760D68DBD753F67F08FDE4BCA08E879C88AAA71F11B04457304240FFFECD02BFC8C338AC1489FE0D11A321FC5449135073616191938159BF59AE41592E1FC3F3B983ABB11D153024083360E7AF2ABC9821D26599C22D85B8E2B6A2CCD0DCC2FE18EF001A218BFC8731CB72D97E0B0584704324B6B496B3A78BAAE95B2C65C11BA239FE5A2CF5011D0D07055B104972FA8DC8607AC33897BAA0A9C218B3C88AB3BC15E1942A4422B1622C25BA04B7403C676F63716A2470BCE708A0DD87E7C7E9F5E1E50D1612443FC42F115E214B947C465062A4B3738792C3ADA49C0A33C7C70BC5C324C927203E422A5257A750579F6685729DF74EE5F3D150A43390F6E0BEE527D698166614DFC3CE17EC53CE41F477D2019F96CE8841B5EFC1EBF152D1FFF6D7E06D76B6421A63FB747003B004B93641207BF4A2D368AC53E41996A980D4A313A4D8576441F8773861044F09006137282098C637C3DA97CDC753DE9780B9F241E79B53432219144E4427240E03070C2623DB916EBEC71CE6E3A1848A83045A494AF95748AA66256B625A04F501186D0F05DBE8008CE5F203DD5A928DDB86FDAFA23F0A68625E3264650225C434200D92DA5F2B2D947F80D6DA9C95B1B2B0B5709C276B4D449A4DD66145130C0406532D24FFBBCDC44195210DBFFB8984C6D3ADA432B84E47FA4A55701E172FE92B3790CE3D3E6CC2FD1FEFF50A82ACB8BEB794E85F568C7FF9416F66174E4748C1356F7C97E186E185A9EFE6DF8473974F5B94F19891AAEEB8B114F01438EAAEFCF193B6181164EE3831126658514147958ED36CA4A78D80848FA5A081D7C8C0470FE61E9210AD253962AD050157484044476D60A7AC8683BAF1145CB12E7E36DBC5FEE39BECCD03DB62D92E1B65B4405D445A44DAAC75819D8D8785F2D4CADA05F1551DE2E8FFDF3A600D20565242426F7009559C95EEBAB8B5EDC322D6E1A2CCD2E50DFD74A7081B331D02A2566D7BB575ED9AE4B66CD50E91ECAA23D7AD2BD1D379F91F242F3A383493DB26A8AC15DE614F339A976FD61DA2AC97FCE9CBC740083B1AFF46F5027F39D0241E007B607F258A62BDD18B865EF77443DF84E5C4F6F6CFE0807C0E065F360F20681B4E461F764F60E5B4C9C198F1C8E743F58981D8B188A7F332494118714867F143090158312921CCD0373FF8F0E8E098908880B8B0A8A058504840788F68601810080038302820DBD3CBC3FBF3EBE39B938B83BBB3ABA35B534B437B736B631B130B033B332B23DAD2CAC2FAF2EAE29A928A82BAB2AAA25A524A427A726A621A120A023A322A22DDD5CDC5FDF5EDE59D958D85BDB5ADA55D554D457D756D651D150D053D352D25DCD4CCC4FCF4ECE49C948C84BCB4ACA45C544C447C746C641C140C043C342C24DFD7CFC7FFF7EFE79F978F87BFB7AFA75F574F477F776F671F170F073F372F27DED6CEC6FEF6EEE69E968E86BEB6AEA65E564E467E766E661E160E063E362E261A120A023A322A225A524A427A726A629A928A82BAB2AAA2DAD2CAC2FAF2EAE21B130B033B332B235B534B437B736B639B938B83BBB3ABA3DBD3CBC3FBF3EBE31810080038302820585048407870686098908880B8B0A8A0D8D0C8C0F8F0E8E01911090139312921595149417971696199918981B9B1A9A1D9D1C9C1F9F1E9E11E160E063E362E265E564E467E766E669E968E86BEB6AEA6DED6CEC6FEF6EEE61F170F073F372F275F574F477F776F679F978F87BFB7AFA7DFD7CFC7FFF7EFE71C140C043C342C245C544C447C746C649C948C84BCB4ACA4DCD4CCC4FCF4ECE41D150D053D352D255D554D457D756D659D958D85BDB5ADA5DDD5CDC5FDF5EDE55A524A427A726A621A120A023A322A22DAD2CAC2FAF2EAE29A928A82BAB2AAA25B534B437B736B631B130B033B332B23DBD3CBC3FBF3EBE39B938B83BBB3ABA358504840787068601810080038302820D8D0C8C0F8F0E8E098908880B8B0A8A059514941797169611911090139312921D9D1C9C1F9F1E9E199918981B9B1A9A15E564E467E766E661E160E063E362E26DED6CEC6FEF6EEE69E968E86BEB6AEA65F574F477F776F671F170F073F372F27DFD7CFC7FFF7EFE79F978F87BFB7AFA75C544C447C746C641C140C043C342C24DCD4CCC4FCF4ECE49C948C84BCB4ACA45D554D457D756D651D150D053D352D25DDD5CDC5FDF5EDE59D958D85BDB5AD'
                DataPayload = list(codecs.decode(DataPayloadhex, 'hex'))
                UDS_TransferData(bus,0x714,DataPayload)
                UDS_TransferExit(bus,0x714)

                sys.exit(0)

                # Neuer Ansatz DAKU

                # 01 44 03 FF 20 78 00 00 00 70
                #Addr: 0x03FF2078 Size: 0x00000070
                Addresse=0x00
                while True:
                 print("\n Addr: 0x%2.2x"%(Addresse))
                 if(UDS_RequestDownload(bus,0x714,[0x01,0x44,0x03,0xFF,Addresse,0x00,0x00,0x00,0x00,0x10])):
                   DataPayloadhex = '00000000000000000000000000000000'
                   DataPayload = list(codecs.decode(DataPayloadhex, 'hex'))
                   UDS_TransferData(bus,0x714,DataPayload)
                   UDS_TransferExit(bus,0x714)
                 
                 Addresse=Addresse+1
                 #if Addresse == 0x40: sys.exit(0)

                sys.exit(0)

                #UDS_RequestDownload(bus,0x714,[0x01,0x44,0x03,0xFF,0x20,0x78,0x00,0x00,0x00,0x70])
                DataPayloadhex = 'DB81EDC5DB3215E03A2B0204BE0E8DD99A9342448E716D26FAD382847A73A2A46629CC8E09F9CBE21D140C05F40C27659E178A04754A6D6594D54BC4F58AADA59C9FA58F6C00E5DF582906061E082E27386940465E486E64F8A98086BEBC8EB0DE868FCC1CFF0F1B5E4567558EFAAA22'
                DataPayload = list(codecs.decode(DataPayloadhex, 'hex'))
                UDS_TransferData(bus,0x714,DataPayload)

                UDS_TransferExit(bus,0x714)

                sys.exit(0)


                CtrlPayloadhex ='FF0044DD00000000000010'
                CtrlPayload =list(codecs.decode(CtrlPayloadhex, 'hex'))
                UDS_RoutineControl2(bus,0x714,0x01,CtrlPayload)
                

                #sleep(0.1)
                ## 100D3101FF004404
                #WorkingFrame = [0x10,0x0D,0x31,0x01,0xFF,0x00,0x44,0x04]
                #msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                #bus.send(msg)

                #sleep(0.1)
                ## 2100000000000010
                #WorkingFrame = [0x21,0x00,0x00,0x00,0x00,0x00,0x00,0x10]
                #msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                #bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout
                #print (recv_message.data)

                # Problem
                # can0  77E   [8]  03 7F 31 22 AA AA AA AA

                sys.exit(0)

                sleep(1.2)
                # 210035555555555
                WorkingFrame = [0x02,0x10,0x03,0x55,0x55,0x55,0x55,0x55]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout
                #print (recv_message.data)
                
                sleep(0.1)
                # 0210605555555555
                WorkingFrame = [0x02,0x10,0x60,0x55,0x55,0x55,0x55,0x55]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout
                #print (recv_message.data)

                sleep(0.1)
                # 052EFD1106AA5555
                WorkingFrame = [0x05,0x2E,0xFD,0x11,0x06,0xAA,0x55,0x55]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout
                #print (recv_message.data)

                sleep(0.1)
                # 300F555555555555
                WorkingFrame = [0x30,0x0F,0x55,0x55,0x55,0x55,0x55,0x55]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                recv_message = bus.recv(2.0) # 2 s Timeout
                #print (recv_message.data)

                sleep(0.1)
                # 042EFD1101555555
                WorkingFrame = [0x04,0x2E,0xFD,0x11,0x01,0x55,0x55,0x55]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout

                sleep(0.1)
                # 101D2EFD11031469
                WorkingFrame = [0x10,0x1D,0x2E,0xFD,0x11,0x03,0x14,0x69]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout

                sleep(0.1)
                # 217F78F11C00DE57
                WorkingFrame = [0x21,0x7F,0x78,0xF1,0x1C,0x00,0xDE,0x57]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout

                sleep(0.1)
                # 225707D989E8BCE4
                WorkingFrame = [0x22,0x57,0x07,0xD9,0x89,0xE8,0xBC,0xE4]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout

                sleep(0.1)
                # 23052E71D2B272A8
                WorkingFrame = [0x23,0x05,0x2E,0x71,0xD2,0xB2,0x72,0xA8]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout

                sleep(0.1)
                # 2457075555555555
                WorkingFrame = [0x24,0x57,0x07,0x55,0x55,0x55,0x55,0x55]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout

                sleep(0.1)
                # 300F555555555555
                WorkingFrame = [0x30,0x0F,0x55,0x55,0x55,0x55,0x55,0x55]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                #recv_message = bus.recv(2.0) # 2 s Timeout


                sys.exit(0)

                #####alter VAgTacho Ansatz

                UDS_RequestDownload(bus,0x714,[0x01,0x44,0x03,0xFF,0x19,0x00,0x00,0x00,0x06,0x00])

                sys.exit(0)

                UDS_WriteDataByIdentifier(bus,0x714,0xF15A,[0x11,0x22,0x33,0x44,0x55,0x66,0x77,0x88,0x99])

                UDS_RequestDownload(bus,0x714,[0x01,0x44,0x03,0xFF,0x19,0x00,0x00,0x00,0x06,0x00])

                #DataPayloadhex = '5F5EB0B19821445A4F475F576F677F773155CDEC0ED1DF2498B1364F05D29A7A905F62620700344B7D17D99D99E152B8029EF2C0B59F7D96F18F42A8E14AEE60'             
                DataPayloadhex = '5F5EB0B19821445A4F475F576F677F773155CDEC0ED1DF2498B1364F05D29A7A905F62620700344B7D17D99D99E152B8029EF2C0B59F7D96F18F42A8E14AEE60B2F3CE4A444F166968C0D9FE9EFCDAB1F4D2C49CF4FCE4ECCB96E4867E41DBAC95E2CBBC757DE5629AEC043DBD0F9CD0AADDC5CDD4D520ED50B7A5BBD1BDE38590704772B150A753D330C5233734650F529CFD411AF5C2A0ED9A7D754D455D55ACA4BCB4F07C806B9318E30C533A1E2DD3EB3C34D3CDB9EBD3AC117EF3BC375ED0A7D848B19E9F68F2ED9D373138272E09271AC54D07E1E8F1624A8D30476CAAB45C23B3BB7CE1969B1D81025179406B5BFC5CC6F0F9E0EF4C667B840C96A0A993984E717CBB2651F4DF53DBF3F86611DC0386F1C43F9323575885B1DC737B21969F8E8937BF3DBA5720DBCD4800C3108AE0060F28398CD0DD525A40767F6669C29C3E89945AF1AC6B23CC33740394EC081AAFF3BE89A1291472BB4F91536BAD959540BBB19DC19F5FF085F30AFE02D214DD95379C180D2B556DBAB232339A6E1BD5834BF38025AA9A95C2CAB3B88AD0F3EF4244CD39AB655B9B02648D790A2076B48E4AB789E3952CD8A4FCFD3A39EE161DB3E8993E22212C5B434B527D4DAA6E9B61BFB1B8229A012521F7F1F861D29915014A517F2028B1174148F132C195B99F81B94E462986D0D9C181F4CFA1E9592E01097817DE2A1013C849F9466069979CAE84B3C1C62F776B8EBCF68059AD7618464F5630666C51292ECF5779262EB690C7CF88FFE7EFB69987BF48400680545F0261767FE258161F46259109744A95EBC0CC71C3E5ECD5B623B2E7D9E593515CC44B007F646C141C040C343C242C55DA24FDD503BFEDD5621778F5BA315875BBC7B055A3E5903533A5F2E932252DD33299E5F2FA5D1548675FA44D452A800975424ACD85AE9749F5020A8DC5E6D7F3ED99CBB3CC711ED39C177E93FD02548F54434B283C636BACE4ABF60E3D231B2F27DD18B82AFF124C8F8088EB47A0A8EFA7D0B5EB7761684A1700082D3061FA9AD320186B0CFEDB4D0E8189EA8EA1A9EEA631B4EA4660694C260A09ED3E21295719F83FB738462F6A59477F8880FA90949F3A80B4BF6F5508D67830B1007AE01F1EBB213F3EBB195D5EFB717D7E3B61929EDBA1B3BEFB99D0DE9BF1F1FEA6E86A1D050DB53AC43D75A31F4D3582F798D59A117895532550F5F3653235F267104933040C8BC3D8D0685A447C8B83F85B979CD9BBB4BC1B533E2078F3F7FCB9D3131BBCF4EDC73FF31781D80C727B3E2C939B3C747D47BFA392018BC11222091ED21D80F7723CDD3AD15D414A92556B9CB39C82BA4D452286A2EAC4F4C6E862D66131892370162329216900667D79205E9299C0BEBCB94196DA2F41F581B9E9A7684E80444000A81211674448003821579E98C1CFB5B8E1EFDFD883CEEFF8E0E8CC58845F3739986C5751F80CBF782E367E90CED6B71118EC0A708C966FFD77E516B8B94D3670996D5630F90D8AD92D3757D1CBD753D1EBF75ED74E64F68059ADD2624A54BC94B88CCD17D527757BDA2E7D9ACAD434D42DD750A4A38BB58D5A52D213494CD293696CD35DD84DB2DB2B2C0C96142652F3EBEC5D754C6E695D78A59B524A4653457F6B2D5D170B1A3D33322C24CBFE34151CEB957B7E6C33BBAC8117BB80A8BB9B5E65131A04EA33373F228ED0C217131D62EAD77BDA60B4B25FA5D1595AA134709D86911902ECD0D601CBD4D41A20F6142700CDA38864D956A0A9141A7E965C789B29CACDDD06CF38A42212D209C1D1CFE1E89578DD69ADB03CA296AA81B74B8827AF36E8E78DF41A20DE102ADA3E32D761C695B59A0672726E5A81ABAFC9B7BEA096D0065AF46E24EEE64D37E101B63EC32176144CA37A9B68B35D9480A08B9284ADD2D003C4281CD93416203B32103DFE0454187B0A5C7D405453DDACBDBDB1BDA112D59FCA2BECE4EC971BE71CB43F192A546CBBB3E983676C2E94808B2E94A6AB0B2113C14E1CE6EBCC12CB21F212E6CAECA42BB572A3436532883D750C461F9DDBDA5FC5FBFA2AD8D413BDF5F0C01923B3BBF84F7340E251F191C28F4EA924EED0D980E359BFB28C505E0709B4762029F817122C30366669EF988088B0B8A0A8D0D8C0C8F0F8E0E810180008303820285058404800000101'
                DataPayload = list(codecs.decode(DataPayloadhex, 'hex'))
                UDS_TransferData(bus,0x714,DataPayload)

                UDS_TransferExit(bus,0x714)
                
                CtrlPayloadhex ='02020403FF1900008072F89CC405F1EF336BCD757353FB38220EAF220C8BE72B5F7183813C68B2BDC382EF408294111D71041710C52682FAA89DD175CD9C3950AF52E4C88C6ABDF3CFCF58FD406E78ED94619B90919247CA0B66146B4F7D463887ACD2D9770B665B892DCA1B7F1B486E58CF983D63A721067B366FB9E829501BC65FBA872BBE26AA59'
                CtrlPayload =list(codecs.decode(CtrlPayloadhex, 'hex'))
                UDS_RoutineControl2(bus,0x714,0x01,CtrlPayload)

                UDS_RequestDownload(bus,0x714,[0x01,0x44,0x03,0xFF,0x18,0x00,0x00,0x00,0x00,0x60])
                
                DataPayloadhex2 = '173DCBA50640262E66A0464EFE7E666E9DC04B25E08AF09AD9DEC9CECD4CE6EE1E94CAA4C8C0D8D0A8A0B8B08880989094F24A24E18BF19BD8DFCFCFCC4DE7EF1E96C9A7CBC3DBD3ABA3BBB38B839B93940849274B435B532B233B330B031B13'                               
                DataPayload2 = list(codecs.decode(DataPayloadhex2, 'hex'))
                UDS_TransferData(bus,0x714,DataPayload2)

                UDS_TransferExit(bus,0x714)                

                CtrlPayloadhex2 ='02020403FF18000080BF1483037145D8B7B9B4475416896A680CE3EEE1273269254762996398A0C537D7F5E3EDC679E97C8AB68DA280B0B97926DFED2FDB2B5209D605D2754BD9982D390106DB245A28CEEE3B884432E5EB644BC78D8A94125E3220CB49E570463AC6030BAE2E234B435F1F09891476D790871437B5F0DF8CD4A396882A627E42BB5C'
                CtrlPayload2 =list(codecs.decode(CtrlPayloadhex2, 'hex'))
                UDS_RoutineControl2(bus,0x714,0x01,CtrlPayload2)
                
                UDS_SecurityAccess2(bus,0x714)
                
                #UDS_ReadMemoryByAddress(bus,0x714,0x00,0x01,0x0100,0x20)
                
                WorkingFrame = [0x23,0x80,0x00,0x12,0x34,0x56,0x78,0xAB]               
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                recv_message = bus.recv(2.0) # 2 s Timeout                   

                # a31d70f3 6a297fa0 7d9a406d 26247b97

                WorkingFrame = [0x3D,0x80,0x13,0xA0] + list(codecs.decode('26247b97', 'hex'))               
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                recv_message = bus.recv(2.0) # 2 s Timeout 
                
                WorkingFrame = [0x3D,0x80,0x13,0xA4] + list(codecs.decode('7d9a406d', 'hex'))            
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                recv_message = bus.recv(2.0) # 2 s Timeout 
                
                WorkingFrame = [0x3D,0x80,0x13,0xA8] + list(codecs.decode('6a297fa0', 'hex'))          
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                recv_message = bus.recv(2.0) # 2 s Timeout 
                
                WorkingFrame = [0x3D,0x80,0x13,0xAC] + list(codecs.decode('a31d70f3', 'hex'))           
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                recv_message = bus.recv(2.0) # 2 s Timeout 


                # Die ersten 4 Byte eeprom lesen
                WorkingFrame = [0x23,0x80,0x00,0x00,0x00,0x00,0x00,0x00]               
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                recv_message = bus.recv(2.0) # 2 s Timeout  
                print (recv_message.data)
                
                #Magic ...                
                sys.exit(0)
                
                UDS_Boot_ExitBl(bus,0x714)
                sleep(1)
                TachoReset(bus,0x714)
                sleep(2)
                recv_message = UDS_WriteDataByIdentifier(bus,0x714,0xFD11,[0x01])
                if recv_message.data[2] == 0x07:
                  print ("Engeneering Mode Access OK")
                else:
                  print ("Error entering Engeneering mode")
                  sys.exit(0)
                
                AesKey= UDS_ReadMemoryByAddress(bus,0x714,0x00,0x01,0x0100,0x20)   
                print( "AesKey: " + str( codecs.encode( AesKey ,'hex') ) )            
                sys.exit(0)    
                
            if (sys.argv[1]) == "-SecAcc2":                

                print(hex(BLSeed2(0x1B4C5F8A))) 
                sys.exit(0)    
                
            if (sys.argv[1]) == "-ExitBl":
                UDS_Boot_ExitBl(bus,0x714)
                sys.exit(0)  

            if (sys.argv[1]) == "-ExitEngeneeringMode":
                UDS_WriteDataByIdentifier(bus,0x714,0xFD11,[0x02,0x02])
                UDS_WriteDataByIdentifier(bus,0x714,0xFD11,[0x05])
                sys.exit(0)                  

            if (sys.argv[1]) == "-TachoReset":
                TachoReset2020(bus,0x714)
                sys.exit(0)                 
            
            if (sys.argv[1]) == "-ReadAesKey":  
                UDS_Boot_ExitBl(bus,0x714)
                sleep(1)
                TachoReset(bus,0x714)
                sleep(2)
                recv_message = UDS_WriteDataByIdentifier(bus,0x714,0xFD11,[0x01])
                if recv_message.data[2] == 0x07:
                  print ("Engeneering Mode Access OK")
                else:
                  print ("Error entering Engeneering mode")
                  sys.exit(0)
                
                AesKey= UDS_ReadMemoryByAddress(bus,0x714,0x00,0x01,0x0100,0x20)   
                print( "AesKey: " + str( codecs.encode( AesKey ,'hex') ) )            
    
                sys.exit(0)   

            if (sys.argv[1]) == "-SetCPState":
	       #0x08 ist der OK State
               CPData = list(codecs.decode(sys.argv[2], 'hex'))

               recv_message = UDS_WriteDataByIdentifier(bus,0x714,0x0956,CPData)
               if len(recv_message) != 0x00:
                  #if recv_message[0] == 0x09 and recv_message[1] == 0x56:
                     print(recv_message)
                     print(" Write CPState  OK")
               else:
                     print(" Write CPState Error")
                     print(recv_message)



            if (sys.argv[1]) == "-WriteCPdata":
                 #arg[2] 34 Byte UDS Daten
                 #arg[3] tacho oder ACC 0714 0757

                 #print("Debug DNN")         
                 #print("Go to EnableEngeneeringMode")
                 #if EnableEngeneeringMode(bus) == False:
                 #  return

    
                 CPDatum = [0x23,0x02,0x26]
                                         #C5D089A911066AC0744A669F99854DCDC83CAC771B6124CFADC06808129A63AA0B57 19 11 26 26.11_17.24Uhr
                                         #1B0CF236F9292DD8A87F0810C45782D3FA6A842A974288AD323E0A911EF886960B57 19 11 26 18.24 Uhr
                                         #136C9C52A143F41D484A486789A7C7338A7B6B55BD82FAF36B8D99AAE474EDAB0B57
                                         #1CCBEE6FC8426FAC0E7215638A3336D6A8AA325DAC1155BB67971388B4A04F800B57
                                         #D9C6154E583ADA0C0D4074604C410E3896D6EBDEC09A70957EFEEE80D7D6C89D0B57
                                         
                                         #WVWZZZ7NZJV007913
                                         #858FC6BB86F951A16036DD1529A4BB7099857D0B4EDFE437A596C70499F4BF050B57
                                         
                 CPData = list(codecs.decode(sys.argv[2], 'hex'))
                 CPDevice = int(sys.argv[3],16)
                 print("Device: %d %x"%(CPDevice,CPDevice))
                 CPID = int(sys.argv[4],16)
                 print("CPID: %d %x"%(CPID,CPID))
                 #for byte in range(0x10,0x100): # 
                     # Byte[33] last byte can be changed    
                     # 0x14 ==> Cp DIsabled für ACC
                     # 0x57 ==> OK Normal
                     # 0x73 115 ==> Akzeptiert, CP Communikation, alles ok
                     # 0xff 255 ==> Akzeptiert, CP Communikation, alles ok
                     
                     # Byte[32] 
                     # 0x0B ==> Normal
                     # 0x00 ==> Works,too
                     # 0xFF ==> Works,too
                     
                    #CPData[32] = byte
                    #print (CPData[30:34],end= ' ')
                 WriteCPData(bus,CPData,CPDatum,CPDevice,CPID)
                    #sleep(2)
                    #TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x03DE)
                    #print("Acc CP Error Counter: " +str(codecs.encode( bytearray(TmpData[2:4]) ,'hex') ))
                    #TmpData = UDS_ReadDataByIdentifier(bus,0x757,0x3C0A)                
                 sys.exit(0)
                
            if (sys.argv[1]) == "-ReadEeprom0x13A0":    
                 Addr = 0x13A0
                 TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x04,0x00,Addr,0x10)
                 #print(TmpData,end='')
                 print( " "+str(str(hex(Addr)))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )                   
                 sys.exit(0)   

            if len(sys.argv) > 1:
                if (sys.argv[1]) == "-WriteEeprom0x13A0":
                    AddrEeprom = int(sys.argv[2],16)
                    #print (AddrEeprom)
                    #return
                    CPEepromData = list(codecs.decode(sys.argv[3], 'hex'))
                    print (UDS_WriteMemoryByAddress(bus,0x714,0x04,0x00,AddrEeprom,CPEepromData)) 
                
            if (sys.argv[1]) == "-TEST2":     
                print("SeedAnswer: 0x%x" %(BL_Seed(0x1D45723C) ) )
                sys.exit(0)
                
                SeedVal64=0x1D45723C
                
                SeedVal = np.uint32(SeedVal64)
                print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))              
                SeedVal = np.uint32(SeedVal) << 1
                print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
                if SeedVal > 0xFFFFFFFF:
                    print("SeedVal > 0xFFFFFFFF Seedval:%x"%(SeedVal64))
                    for i in range(0,0x12):
                        SeedVal = np.uint32(SeedVal) << 1
                        if SeedVal > 0xFFFFFFFF:
                            SeedVal = SeedVal ^ 0x2FB67A9C
                            SeedVal = np.uint32(SeedVal) << 1
                            SeedVal = np.uint32(SeedVal)
                            SeedVal = SeedVal - 0x35658453
                            if SeedVal > 0xFFFFFFFF:
                                SeedVal = SeedVal ^ 0x20142BCD
                                SeedVal = SeedVal + 0x0BFB83250
                        else:
                            SeedVal = SeedVal ^ 0x20142BCD
                            SeedVal = SeedVal + 0x0BFB83250                            
                
                else:
                
                    for i in range(0,0xB):
                        SeedVal = np.uint32(SeedVal)
                        SeedVal = SeedVal + 0x0DAE7823C
                        print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
                        if SeedVal > 0xFFFFFFFF:
                            SeedVal = SeedVal ^ 0x3DCEE873
                            print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
                            SeedVal = np.uint32(SeedVal)
                            SeedVal = SeedVal + 0x48904532
                            print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
                            if SeedVal > 0xFFFFFFFF:
                                  SeedVal = SeedVal << 1
                                  SeedVal = SeedVal ^ 0x0D68A42B
                                  SeedVal = SeedVal << 1
                
                print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
                SeedVal = np.uint32(SeedVal) << 1
                SeedVal = SeedVal + 1
                #SeedVal = np.uint32(SeedVal)
                print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))
                SeedVal = np.uint32(SeedVal) ^ 0x0A16532CD
                print ("SeedVal: 0x%x type: %s" % (SeedVal,type(SeedVal)))

                sys.exit(0)                  

        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoDumpRamVagtacho":
                #TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x00,0x01,0x0100,0x20)
                #print(TmpData,end='')
                #print( " "+str(hex(Tel))+" "+str(hex(Sel))+" "+str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )

                FilenamePrefix = "Vagtacho"
                if len(sys.argv) > 2 and sys.argv[2] != "":
                   Directory = sys.argv[2]
                else:
                   Directory = "./"
                TachoDumpRam(bus,Directory+FilenamePrefix)
                sys.exit(0)


        
        print("Go to EnableEngeneeringMode")

        if EnableEngeneeringMode(bus) == False:
            return
            #pass

        UDS_TesterPresent(bus,0x714)

        if (sys.argv[1]) == "-ImmoRead":
           for ucCnt in range (0,8):
            TmpData = UDS_ReadDataByIdentifier(bus,0x714,0xFEE8,ucCnt)
            del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
            print("Immo: " +str(codecs.encode( bytearray(TmpData) ,'hex') ))
            #print(          str(codecs.encode( bytearray(TmpData) ,'hex') ))

           sys.exit(0)

        if (sys.argv[1]) == "-UDS_RequestUpload_ENG":
          #for byte in range(1,2):
           #sleep(1)
          UDS_RequestUpload(bus,0x714,[0x01,0x44,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00])
          sys.exit(0)


        if (sys.argv[1]) == "-TachoDumpCpKeyRAM":
         TachoDumpCpKeyRAM(bus)
         sys.exit(0)
        
        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoWriteCPEeprom":
                AddrEeprom = int(sys.argv[2],16)
                #print (AddrEeprom)
                #return
                CPEepromData = list(codecs.decode(sys.argv[3], 'hex'))
                print (UDS_WriteMemoryByAddress(bus,0x714,0x04,0x00,AddrEeprom,CPEepromData)) 
                
        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoWriteFlash":
                AddrFlashUp = int(sys.argv[2],16)
                AddrFlash = int(sys.argv[3],16)
                FlashData = list(codecs.decode(sys.argv[4], 'hex'))
                #print (UDS_WriteMemoryByAddress(bus,0x714,0x00,AddrFlashUp,AddrFlash,FlashData))
                Addr3  = 0xFF
                Addr2  = 0xFF     
                AddrHi = 0xFF
                AddrLo = 0xFF          
                DataSizeLo = 0x02
                WorkingFrame = [0x10,DataSizeLo+10,0x3D,0x44,Addr3,Addr2,AddrHi,AddrLo]
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                recv_message = bus.recv(2.0) # 2 s Timeout
                print (recv_message)
                
                WorkingFrame = [0x20+1,0x00,0x00,0x00,DataSizeLo] + FlashData[0:2]
                WorkingFrame = FillUpCanFrame(WorkingFrame)
                msg = can.Message(arbitration_id=0x714,data=WorkingFrame,is_extended_id=False)
                bus.send(msg)
                recv_message = bus.recv(2.0) # 2 s Timeout
                print (recv_message)



        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoReadFlash": 
                AddrFlashUp = int(sys.argv[2],16)
                AddrFlash = int(sys.argv[3],16)
                TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x00,AddrFlashUp,AddrFlash,0x10)
                print( " Data: " +str( codecs.encode( bytearray(TmpData) ,'hex') )) 


        
        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-ReadInfo":      
                
                #for Identifier in [0xF189]:
                for Identifier in [0xF189,0xF1A2,0xF190,0x2292,0x2203,0x2216,0xF17C,0xF19E,0x0600,0x0956,0xF197]:
                
                    TmpData = UDS_ReadDataByIdentifier(bus,0x714,Identifier)
                    del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
                    print(TmpData,end= '  ')
                    print( str( codecs.encode( bytearray(TmpData) ,'hex') ) )
        
        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-ReadCPEepromData":    
                #Addr=0x13A0
                #TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x04,0x00,Addr,0x20)
                #print(TmpData,end='')
                #print( " "+str(str(hex(Addr)))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )                       
                TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x04,0x00,0x10E,0x01)
                print( " "+str(str(hex(0x10E)))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )
                for Addr in range(0x1500,0x1700,0x20):            
                 #Addr=0x1500
                 TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x04,0x00,Addr,0x20)
                 #print(TmpData,end='')
                 print( " "+str(str(hex(Addr)))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )                    
 
        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-ReadEepromData":     
                AddrEeprom = int(sys.argv[2],16)
                TmpData = UDS_ReadMemoryByAddress(bus,0x714,0x04,0x00,AddrEeprom,0x20)
                #print(TmpData,end='')
                print( " "+str(str(hex(AddrEeprom)))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )  
       
        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoDumpRam":
                FilenamePrefix = TachoIDString(bus)                      
                if len(sys.argv) > 2 and sys.argv[2] != "":
                   Directory = sys.argv[2]
                else:
                   Directory = "./"
                TachoDumpRam(bus,Directory+FilenamePrefix)
                
        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoShowRam":
              AddrIn = int(sys.argv[2],16)
              SizeIn = int(sys.argv[3],16)

              for Addr in range(AddrIn,AddrIn+SizeIn,0x20):
               if Addr == 0xf560: # Read ==> Tacho Reset
                 print("not supported")
               else:
                TmpData = UDS_ReadMemoryByAddress(bus,0x714,255,255,Addr,SizeIn)
                #TmpData = UDS_ReadMemoryByAddress(bus,0x714,0xBF,0xFD,Addr,0x20)
                #print(TmpData,end='')
                print( " "+str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) )


        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoDumpRamVars":
                for Addr in (0x00,0xb504,0x7b40,0x7b60,0x7b80,0x7bA0,0x7bC0,0x7bE0,0x7c00,0xb8a1,0xb8b8,0x6f10,0xb8a3,0xBEBD):
                    TmpData = UDS_ReadMemoryByAddress(bus,0x714,255,255,Addr,0x20)
                    print( " "+str(str(hex(Addr))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') ) ) )
                
        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoDump3DFlash":
                FilenamePrefix = TachoIDString(bus)
                if len(sys.argv) > 2 and sys.argv[2] != "":
                   Directory = sys.argv[2]
                else:
                   Directory = "./"
                TachoDump3DFlash(bus,Directory+FilenamePrefix)

        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoDump3DCode":
                FilenamePrefix = TachoIDString(bus)
                print(FilenamePrefix)
                if len(sys.argv) > 2 and sys.argv[2] != "":
                   Directory = sys.argv[2]
                else:
                   Directory = "./"
                TachoDump3DCode(bus,Directory+FilenamePrefix)

        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoDumpGeneriq":
             addr3 = int(sys.argv[2],16)
             addr2 = int(sys.argv[3],16)
             addr1 = int(sys.argv[4],16)
             size = int(sys.argv[5],16)

             for addr3 in range (0x00,0x100,0x01): 
              TmpData = UDS_ReadMemoryByAddress(bus,0x714,addr3,addr2,addr1,size)
              print(" "+str(hex(addr3))+" "+str(hex(addr2))+" "+str(hex(addr1))+" "+str( codecs.encode( bytearray(TmpData) ,'hex') )) 


        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoDumpEeprom":
                FilenamePrefix = TachoIDString(bus)                      
                if len(sys.argv) > 2 and sys.argv[2] != "":
                   Directory = sys.argv[2]
                else:
                   Directory = "./"
                TachoDumpEeprom(bus,Directory+FilenamePrefix)
                
        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoDumpFlash":                      
                FilenamePrefix = TachoIDString(bus)
                if len(sys.argv) > 2 and sys.argv[2] != "":
                   Directory = sys.argv[2]
                else:
                   Directory = "./"
                TachoDumpFlash(bus,Directory+FilenamePrefix)
                
# im engeneering mod egeht reset nicht
#        if len(sys.argv) > 1:
#            if (sys.argv[1]) == "-TachoReset":
#                sleep(5)
#                UDS_Boot_ExitBl(bus,0x714)
#                sleep(5)
#                TachoReset(bus,0x714)
#                sys.exit(0) 
#                
#                recv_message = UDS_WriteDataByIdentifier(bus,0x714,0xFD00,[0x01])
#                print (recv_message)
#                
#                RecID3DB=0
#                DataReceived3DB=bytearray()
#                RecID3EB=0
#                DataReceived3EB=bytearray()                
#                while True:
#                    recv_message = bus1.recv(30.0) # 2 s Timeout
#                    if(recv_message.arbitration_id==0x3DB):
#                      if(recv_message.data[0] != 0x30): # ACk Frsames interessieren nicht
#                        RecID3DB=RecID3DB+1
#                        DataReceived3DB = DataReceived3DB + recv_message.data
#                        if RecID3DB==2:
#                            RecID3DB=0
#                            del DataReceived3DB[8]
#                            del DataReceived3DB[0]
#                            print("Tacho==>ACC: "+str( codecs.encode( bytearray(DataReceived3DB[:3]) ,'hex'))+ " "+str( codecs.encode( bytearray(DataReceived3DB[3:11]) ,'hex'))+" "+hex(DataReceived3DB[11]))
#                            DataReceived3DB=bytearray()
#                            
#                    if(recv_message.arbitration_id==0x3EB): 
#                      if(recv_message.data[0] != 0x30): # ACk Frsames interessieren nicht
#                        RecID3EB=RecID3EB+1
#                        DataReceived3EB = DataReceived3EB + recv_message.data
#                        if RecID3EB==2:
#                            RecID3EB=0
#                            del DataReceived3EB[8]
#                            del DataReceived3EB[0]
#                            print("ACC==>Tacho: "+str( codecs.encode( bytearray(DataReceived3EB[:3]) ,'hex'))+ " "+str( codecs.encode( bytearray(DataReceived3EB[3:11]) ,'hex'))+" "+hex(DataReceived3EB[11]))
#                            DataReceived3EB=bytearray()

        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoDumpIdentifiers":
                for Identifier in range(0x00,0x10000):
                 TmpData = UDS_ReadDataByIdentifier(bus,0x714,Identifier)
                 del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
                 if TmpData != []:
                  print(TmpData,end='')
                  print( str( codecs.encode( bytearray(TmpData) ,'hex') ) )
                  
        if len(sys.argv) > 1:
            if (sys.argv[1]) == "-TachoDumpIdentifiersCp":
                for Identifier in [0x2216,0x2239,0xf15a,0xf198,0xf199,0xf442]:
                 TmpData = UDS_ReadDataByIdentifier(bus,0x714,Identifier)
                 del TmpData[0:2] # die zwei Byte response ID müssen hier noch weg
                 if TmpData != []:
                  print(TmpData,end='')
                  print( str( codecs.encode( bytearray(TmpData) ,'hex') ) )                        

      except can.CanError:
        print("Message NOT sent")

if __name__ == '__main__':
    send_one()

