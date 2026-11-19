# -*- coding: utf-8 -*-
"""
Created initially on Fri Sep 25 22:24:43 2020

@author: Dennis Nörmann
Version 1.0 29. May 2024

This Script Finds with some simple Math the Gear Transmission Tables in EDC17CP20 binary Firmware to show the Addresses for manual Modification.
Initially Build to Patch CAAA Engine with retrotittedt 6 Gear box to support 6th Gear for Cruise Control
Still that is not working, some extra Consitency Check is kiking in and CCS Disengages but gor other Work its still a help

"""

import sys
import re

with open(sys.argv[1], "rb") as f:
    bytes_read = f.read()

#print (type(bytes_read))

pat = re.search(b'03L',bytes_read)                                    
print ("Infos an Adresse: ",end='')                                    
print (hex(pat.start()))
text = str(bytes_read[pat.start():pat.start()+0x75])
print (text)


#################
### Tra_trqMaxGear6_CUR ==> ist immer gleich
### AccMon_rTopGear_C
### AccMon_rFrstGear_C
### MoFDrDem_rTrqPTMax_C
### MoFDrDem_rTrqPTMin_C
### MoFTra_rFrstGear_C
### MoFTra_rTopGear_C


baddr=0x54DBC
GSHDem_rTraGear1_C = bytes_read[baddr+ 1]*256 + bytes_read[baddr+ 0]
GSHDem_rTraGear2_C = bytes_read[baddr+ 3]*256 + bytes_read[baddr+ 2]
GSHDem_rTraGear3_C = bytes_read[baddr+ 5]*256 + bytes_read[baddr+ 4]
GSHDem_rTraGear4_C = bytes_read[baddr+ 7]*256 + bytes_read[baddr+ 6]
GSHDem_rTraGear5_C = bytes_read[baddr+ 9]*256 + bytes_read[baddr+ 8]
GSHDem_rTraGear6_C = bytes_read[baddr+11]*256 + bytes_read[baddr+10]
GSHDem_rTraGear7_C = bytes_read[baddr+13]*256 + bytes_read[baddr+12]

print ("GSHDem_rTraGear1_C bis GSHDem_rTraGear7_C (immer gleich)")
print ("%d %d %d %d %d %d %d" % (GSHDem_rTraGear1_C,GSHDem_rTraGear2_C,GSHDem_rTraGear3_C,GSHDem_rTraGear4_C,GSHDem_rTraGear5_C,GSHDem_rTraGear6_C,GSHDem_rTraGear7_C)) 

# GSHDem_rTraGear1_C bis GSHDem_rTraGear7_C ist immer gleich der Folge: 6D 05 01 03 E8 01 68 01 1C 01 ED 00 00 00

#Powerclass
#Sia_WFSKLASSE_C
#"SIA: Leistungsklasse"

#pos=0
#pat = re.findall(b'\x2B\x01\x19',bytes_read,pos)                                    
#print ("")
#print ("PWRClass: ",end='')                                    
#print (len(pat))
#sys.exit()

#pos=0
#pat_Sia_WFSKLASSE_C= re.search(b'\xFF\xFF\x00\x00\x01\x00\x81\x00\x00\x02\x04\x05',bytes_read)
#print ("")
#print ("Sia_WFSKLASSE_C (Powerclass): Addr: 0x%4.4x Value 0x%2.2x " % ((pat_Sia_WFSKLASSE_C.start()+16),bytes_read[pat_Sia_WFSKLASSE_C.start()+16]))                                    
##print (hex(pat_Sia_WFSKLASSE_C.start()+16))
#sys.exit()

pos=0
num=1
#while num < 7:
pat = re.findall(b'\x08\x00\xF6\x04\xB7\x08\x79\x0C\x3A\x10\xFC\x13\xBD\x17\x7F\x1B\x40\x1F\x30\x75\x30\x75\x30\x75\x30\x75\x30\x75\x30\x75\x30\x75\x30\x75',bytes_read,pos)                                    
print ("")
print ("Tra_trqMaxGear1_CUR - Tra_trqMaxGear7_CUR match the same Sequenze: ",end='')                                    
print (len(pat))
#    pos=pat.start()+5
#    num=num+1                    

addr=20
while addr < len(bytes_read)-60:

                    #a = bytes_read[addr]
                    #b = bytes_read[addr+1]
                    #if a == 0x24 and b == 0x01:
                    #    print("0x0124 found @ 0x"+hex(addr))

                    gangmax = int(bytes_read[addr+9]*256) + int(bytes_read[addr+8])
                    gangvor = int(bytes_read[addr+7]*256) + int(bytes_read[addr+6])
                    gangr   = int(bytes_read[addr+5]*256) + int(bytes_read[addr+4])
                    gang9   = int(bytes_read[addr+3]*256) + int(bytes_read[addr+2])
                    gang8   = int(bytes_read[addr+1]*256) + int(bytes_read[addr+0])
                    gang7   = int(bytes_read[addr-1]*256) + int(bytes_read[addr-2])
                    gang6   = int(bytes_read[addr-3]*256) + int(bytes_read[addr-4])
                    gang5   = int(bytes_read[addr-5]*256) + int(bytes_read[addr-6])
                    gang4   = int(bytes_read[addr-7]*256) + int(bytes_read[addr-8])
                    gang3   = int(bytes_read[addr-9]*256) + int(bytes_read[addr-10])
                    gang2   = int(bytes_read[addr-11]*256) + int(bytes_read[addr-12])
                    gang1   = int(bytes_read[addr-13]*256) + int(bytes_read[addr-14])
                    
                    
                    
                    if (gangmax >= gang1 > gang2 > gang3 > gang4 > gang5) and (gang1 >= gangr >= gang2) and (gang1 <2500) and (gang1-200 > gang2) and (gangvor==100):
                            print (" Getriebe Übersetzungstabelle PT_rTraGear1_C ab: " + str(hex(addr-14)) + " bis: " + str(hex(addr+9))  )    
                            print ("  9: " +str(gang9)+" " + hex(gang9))                            
                            print ("  8: " +str(gang8)+" " + hex(gang8))
                            print ("  7: " +str(gang7)+" " + hex(gang7))                            
                            print ("  6: " +str(gang6)+" " + hex(gang6))
                            print ("  5: " +str(gang5)+" " + hex(gang5))
                            print ("  4: " +str(gang4)+" " + hex(gang4))
                            print ("  3: " +str(gang3)+" " + hex(gang3))
                            print ("  2: " +str(gang2)+" " + hex(gang2))
                            print ("  1: " +str(gang1)+" " + hex(gang1))
                            print ("  R: " +str(gangr)+" " + hex(gangr))
                            print ("max: " +str(gangmax)+" " + hex(gangmax))
                            print ("vor: " +str(gangvor)+" " + hex(gangvor))
                            
                            Save_gang1 = gang1
                            Save_gang5 = gang5
                            Save_gang6 = gang6
                            Save_gang7 = gang7
                            
                            
                            if gang7 < gang6 < gang5:
                                gang=7                                
                                print ("==> 7 Gang Getriebe")   
                                # 02 ==> Use Matrix
                                # Which is 8 Posibilities
                                # 04 FF FF FF FF FF FF FF Only 7 Gear, see Page 853 Tabelle 538 Gangstufen                                
                                pat = re.search(b'x02\x04\xFF\xFF\xFF\xFF\xFF\xFF\xFF',bytes_read)                                    
                                print ("BasSvrAppl_CodTraSprdM_CA Codierzelle Getriebespreizung/-übersetzung Addr: ",end='')     
                                #print ("")
                                print (hex(pat.start()+1))
                            else:
                                if gang6 < gang5:
                                    gang=6
                                    print ("==> 6 Gang Getriebe")
                                    # 02 ==> Use Matrix
                                    # Which is 8 Posibilities
                                    # 03 FF FF FF FF FF FF FF Only 6 Gear, see Page 853 Tabelle 538 Gangstufen
                                    
                                    pat = re.search(b'\x02\x03\xFF\xFF\xFF\xFF\xFF\xFF\xFF',bytes_read)
                                    print ("BasSvrAppl_CodTraSprdM_CA Codierzelle Getriebespreizung/-übersetzung Addr: ",end='')     
                                    print (hex(pat.start()+1))
                                                                        
                                else:
                                    gang=5
                                    print ("==> 5 Gang Getriebe")
                                    # 02 ==> Use Matrix
                                    # Which is 8 Posibilities
                                    # 02 FF FF FF FF FF FF FF Only 5 Gear, see Page 853 Tabelle 538 Gangstufen                                    
                                    pat = re.search(b'\x02\x01\xFF\xFF\xFF\xFF\xFF\xFF\xFF',bytes_read)                                    
                                    print ("BasSvrAppl_CodTraSprdM_CA Codierzelle Getriebespreizung/-übersetzung Addr: ",end='')                                    
                                    print (hex(pat.start()+1))
                                    
                    #addr=0x7DF22
                    Tra_rVn1H_C      = bytes_read[addr+1]*256 + bytes_read[addr+0]
                    Tra_rVn1L_C      = bytes_read[addr+3]*256 + bytes_read[addr+2]
                    Tra_rVn1To2Des_C = bytes_read[addr+5]*256 + bytes_read[addr+4]
                    Tra_rVn2H_C      = bytes_read[addr+7]*256 + bytes_read[addr+6]
                    Tra_rVn2L_C      = bytes_read[addr+9]*256 + bytes_read[addr+8]
                    Tra_rVn2To3Des_C = bytes_read[addr+11]*256 + bytes_read[addr+10]
                    Tra_rVn3H_C      = bytes_read[addr+13]*256 + bytes_read[addr+12]
                    Tra_rVn3L_C      = bytes_read[addr+15]*256 + bytes_read[addr+14]
                    Tra_rVn3To4Des_C = bytes_read[addr+17]*256 + bytes_read[addr+16]
                    Tra_rVn4H_C      = bytes_read[addr+19]*256 + bytes_read[addr+18]
                    Tra_rVn4L_C      = bytes_read[addr+21]*256 + bytes_read[addr+20]
                    Tra_rVn4To5Des_C = bytes_read[addr+23]*256 + bytes_read[addr+22]
                    Tra_rVn5H_C      = bytes_read[addr+25]*256 + bytes_read[addr+24]
                    Tra_rVn5L_C      = bytes_read[addr+27]*256 + bytes_read[addr+26]
                    Tra_rVn5To6Des_C = bytes_read[addr+29]*256 + bytes_read[addr+28]
                    Tra_rVn6H_C      = bytes_read[addr+31]*256 + bytes_read[addr+30]
                    Tra_rVn6L_C      = bytes_read[addr+33]*256 + bytes_read[addr+32]
                    Tra_rVn6To7Des_C = bytes_read[addr+35]*256 + bytes_read[addr+34]
                    Tra_rVn7H_C      = bytes_read[addr+37]*256 + bytes_read[addr+36]
                    Tra_rVn7L_C      = bytes_read[addr+39]*256 + bytes_read[addr+38]
                    Tra_rVn7To8Des_C = bytes_read[addr+41]*256 + bytes_read[addr+40]
                    Tra_rVn8H_C      = bytes_read[addr+43]*256 + bytes_read[addr+42]
                    Tra_rVn8L_C      = bytes_read[addr+45]*256 + bytes_read[addr+44]
                    Tra_rVn8To9Des_C = bytes_read[addr+47]*256 + bytes_read[addr+46]                                    
                    Tra_rVn9H_C      = bytes_read[addr+49]*256 + bytes_read[addr+48]
                    Tra_rVn9L_C      = bytes_read[addr+51]*256 + bytes_read[addr+50]
                    Tra_rVnRH_C      = bytes_read[addr+53]*256 + bytes_read[addr+52]
                    Tra_rVnRL_C      = bytes_read[addr+55]*256 + bytes_read[addr+54]
                    
                    if ((Tra_rVn1H_C<Tra_rVn2H_C<Tra_rVn3H_C<Tra_rVn4H_C<Tra_rVn5H_C<=Tra_rVn6H_C<=Tra_rVn7H_C)  and (Tra_rVnRH_C >=Tra_rVnRL_C) and (Tra_rVn1H_C>Tra_rVn1L_C) and (100<Tra_rVnRH_C<1500) and (100<Tra_rVnRL_C<1500) and (Tra_rVn9H_C==Tra_rVn9L_C==32000) ):
                        #and (Tra_rVn8H_C==Tra_rVn8L_C==Tra_rVn9H_C==Tra_rVn9L_C==32000)
                        print (" Tra_rVn1H_C Parameter fuer maximales Uebersetzungsverhaeltnis Gang 1 0x%x bis 0x%x " % (addr,addr+5))
                        print (" Gang 1,2 %4.4d %4.4d %4.4d %4.4d %4.4d %4.4d" % (Tra_rVn1H_C,Tra_rVn1L_C,Tra_rVn1To2Des_C,Tra_rVn2H_C,Tra_rVn2L_C,Tra_rVn2To3Des_C))                                    
                        print (" Gang 3,4 %4.4d %4.4d %4.4d %4.4d %4.4d %4.4d" % (Tra_rVn3H_C,Tra_rVn3L_C,Tra_rVn3To4Des_C,Tra_rVn4H_C,Tra_rVn4L_C,Tra_rVn4To5Des_C))
                        print (" Gang 5,6 %4.4d %4.4d %4.4d %4.4d %4.4d %4.4d" % (Tra_rVn5H_C,Tra_rVn5L_C,Tra_rVn5To6Des_C,Tra_rVn6H_C,Tra_rVn6L_C,Tra_rVn6To7Des_C))
                        print (" Gang 7,8 %4.4d %4.4d %4.4d %4.4d %4.4d %4.4d" % (Tra_rVn7H_C,Tra_rVn7L_C,Tra_rVn7To8Des_C,Tra_rVn8H_C,Tra_rVn8L_C,Tra_rVn8To9Des_C))
                        print (" Gang 9 %4.4d %4.4d" % (Tra_rVn9H_C,Tra_rVn9L_C))
                        print (" Gang R %4.4d %4.4d" % (Tra_rVnRH_C,Tra_rVnRL_C))      

                        print (" Start: Hex: %x" %(Tra_rVn1H_C))
                        print (" Stop : Hex: %x" %(Tra_rVnRL_C))                              
                                                        
                    ACCI_nEngLoLim_C  = bytes_read[addr-3]*256 + bytes_read[addr-4]                                  
                    ACCI_nEngLoOfs_C  = bytes_read[addr-1]*256 + bytes_read[addr-2]   
                    ACCI_numGearMax_C = bytes_read[addr]
                    ACCI_numGearMin_C = bytes_read[addr+1]
                    
                    if (ACCI_nEngLoLim_C==0x0640 and ACCI_nEngLoOfs_C==0x01F4):
                        print ( "ACCI_numGearMax_C 0x%x addr: 0x%x ACCI_numGearMin_C 0x%x addr: 0x%x " % (ACCI_numGearMax_C,addr,ACCI_numGearMin_C,addr+1))
                    
                    Com_daACCDes_C       = bytes_read[addr-2]
                    Com_swtACCTyp_C      = bytes_read[addr-1]
                    Com_numGearMax_C     = bytes_read[addr]
                    Com_swtGearInfoMT1_C = bytes_read[addr+1]
                    Unknown1_8Bit        = bytes_read[addr+2]
                    Unknown2_8Bit        = bytes_read[addr+3]            
                    ACCI_aTolMax_C       =  bytes_read[addr+5]*256 + bytes_read[addr+4] 

                    if ( Com_daACCDes_C == 0 and Com_swtACCTyp_C == 1 and (Com_numGearMax_C==5 or Com_numGearMax_C==6 or Com_numGearMax_C==7 or Com_numGearMax_C==0) and  (Com_swtGearInfoMT1_C == 1 or Com_swtGearInfoMT1_C == 0) and Unknown1_8Bit == 0 and Unknown2_8Bit == 0  and ACCI_aTolMax_C == 0x07D0):
                    #if ( Com_daACCDes_C == 0 and Com_swtACCTyp_C == 1 and (Com_numGearMax_C==5 or Com_numGearMax_C==6 or Com_numGearMax_C==7) and  Com_swtGearInfoMT1_C == 0 and Unknown1_8Bit == 0 and Unknown2_8Bit == 0  and ACCI_aTolMax_C == 0x07D0):    
                        print ("Maxgang = %d Com_numGearMax_C addr: 0x%x" % (Com_numGearMax_C,addr))
                                       
                    
                    #GSHDem_rTraGear1_C
                    #GSHDem_rTraGear7_C                                   
                                   

                    addr=addr+1
                        
addr=60
#print ("Gang1 %d 0x%x"% (Save_gang1,Save_gang1))
#print ("Gang5 %d 0x%x"% (Save_gang5,Save_gang5))
#print ("Gang6 %d 0x%x"% (Save_gang6,Save_gang6))
#print ("")

while addr < len(bytes_read)-60:
        AccMon_rFrstGear_C = bytes_read[addr] + bytes_read[addr+1]*256
        AccMon_rTopGear_C  = bytes_read[addr+2] + bytes_read[addr+3]*256
        
        
        if AccMon_rFrstGear_C==Save_gang1:
            if gang==7: 
                if (AccMon_rTopGear_C==Save_gang7):
                    print ("AccMon_rFrstGear_C or MoFTra_rFrstGear_C @ "+hex(addr)   +" Ratio: "+hex(Save_gang1))
                    print ("AccMon_rTopGear_C  or MoFTra_rTopGear_C @ "+hex(addr+2) +" Ratio: "+hex(Save_gang7))
                    old_addr=addr
                    addr=addr+2
                    while addr < (old_addr + 32):
                        Unknown_FirstGear = bytes_read[addr] + bytes_read[addr+1]*256
                        if (Unknown_FirstGear==Save_gang1):
                           print ("- MoFVSS_rDrvTrnSubs_C @ 0x"+hex(addr)   +" Ratio: "+hex(Save_gang1) + " Offset: " + hex(addr-old_addr))
                           print (" UpperAddresses are MoFTra_r not AccMon_r\n")
                           
                        addr=addr+1
                        
            if gang==6: 
                if (AccMon_rTopGear_C==Save_gang6):
                    print ("AccMon_rFrstGear_C or MoFTra_rFrstGear_C @ "+hex(addr)   +" Ratio: "+hex(Save_gang1))
                    print ("AccMon_rTopGear_C  or MoFTra_rTopGear_C @ "+hex(addr+2) +" Ratio: "+hex(Save_gang6))
                    old_addr=addr
                    addr=addr+2
                    while addr < (old_addr + 32):
                        Unknown_FirstGear = bytes_read[addr] + bytes_read[addr+1]*256
                        if (Unknown_FirstGear==Save_gang1):
                           print ("- MoFVSS_rDrvTrnSubs_C @ 0x"+hex(addr)   +" Ratio: "+hex(Save_gang1) + " Offset: " + hex(addr-old_addr))
                           print (" UpperAddresses are MoFTra_r not AccMon_r\n")
                           
                        addr=addr+1
                        
            if gang==5: 
                if (AccMon_rTopGear_C==Save_gang5):
                    print ("AccMon_rFrstGear_C or MoFTra_rFrstGear_C @ "+hex(addr)   +" Ratio: "+hex(Save_gang1))
                    print ("AccMon_rTopGear_C  or MoFTra_rTopGear_C @ "+hex(addr+2) +" Ratio: "+hex(Save_gang5))
                    old_addr=addr
                    addr=addr+2
                    while addr < (old_addr + 32):
                        Unknown_FirstGear = bytes_read[addr] + bytes_read[addr+1]*256
                        if (Unknown_FirstGear==Save_gang1):
                           print ("- MoFVSS_rDrvTrnSubs_C @ 0x"+hex(addr)   +" Ratio: "+hex(Save_gang1) + " Offset: " + hex(addr-old_addr))
                           print (" UpperAddresses are MoFTra_r not AccMon_r\n")
                           
                        addr=addr+1
       
        addr=addr+1
        