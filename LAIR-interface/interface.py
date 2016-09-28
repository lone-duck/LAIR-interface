#interface.py
#Author: Dylan Green
#Contact: dylan.green@alumni.ubc.ca
#
#This script interfaces with the IGC-3 Pressure Gauges in the Omicron pod.
#Data is tweeted at https://twitter.com/lair_bot at most once per minute. CSV files
#are generated whenever the program exits or has been running for 24 hours.
#
import csv, tweepy, requests, time, serial, struct, os

#lookup table of crc suffixes
table = (
0x0000, 0xC0C1, 0xC181, 0x0140, 0xC301, 0x03C0, 0x0280, 0xC241,
0xC601, 0x06C0, 0x0780, 0xC741, 0x0500, 0xC5C1, 0xC481, 0x0440,
0xCC01, 0x0CC0, 0x0D80, 0xCD41, 0x0F00, 0xCFC1, 0xCE81, 0x0E40,
0x0A00, 0xCAC1, 0xCB81, 0x0B40, 0xC901, 0x09C0, 0x0880, 0xC841,
0xD801, 0x18C0, 0x1980, 0xD941, 0x1B00, 0xDBC1, 0xDA81, 0x1A40,
0x1E00, 0xDEC1, 0xDF81, 0x1F40, 0xDD01, 0x1DC0, 0x1C80, 0xDC41,
0x1400, 0xD4C1, 0xD581, 0x1540, 0xD701, 0x17C0, 0x1680, 0xD641,
0xD201, 0x12C0, 0x1380, 0xD341, 0x1100, 0xD1C1, 0xD081, 0x1040,
0xF001, 0x30C0, 0x3180, 0xF141, 0x3300, 0xF3C1, 0xF281, 0x3240,
0x3600, 0xF6C1, 0xF781, 0x3740, 0xF501, 0x35C0, 0x3480, 0xF441,
0x3C00, 0xFCC1, 0xFD81, 0x3D40, 0xFF01, 0x3FC0, 0x3E80, 0xFE41,
0xFA01, 0x3AC0, 0x3B80, 0xFB41, 0x3900, 0xF9C1, 0xF881, 0x3840,
0x2800, 0xE8C1, 0xE981, 0x2940, 0xEB01, 0x2BC0, 0x2A80, 0xEA41,
0xEE01, 0x2EC0, 0x2F80, 0xEF41, 0x2D00, 0xEDC1, 0xEC81, 0x2C40,
0xE401, 0x24C0, 0x2580, 0xE541, 0x2700, 0xE7C1, 0xE681, 0x2640,
0x2200, 0xE2C1, 0xE381, 0x2340, 0xE101, 0x21C0, 0x2080, 0xE041,
0xA001, 0x60C0, 0x6180, 0xA141, 0x6300, 0xA3C1, 0xA281, 0x6240,
0x6600, 0xA6C1, 0xA781, 0x6740, 0xA501, 0x65C0, 0x6480, 0xA441,
0x6C00, 0xACC1, 0xAD81, 0x6D40, 0xAF01, 0x6FC0, 0x6E80, 0xAE41,
0xAA01, 0x6AC0, 0x6B80, 0xAB41, 0x6900, 0xA9C1, 0xA881, 0x6840,
0x7800, 0xB8C1, 0xB981, 0x7940, 0xBB01, 0x7BC0, 0x7A80, 0xBA41,
0xBE01, 0x7EC0, 0x7F80, 0xBF41, 0x7D00, 0xBDC1, 0xBC81, 0x7C40,
0xB401, 0x74C0, 0x7580, 0xB541, 0x7700, 0xB7C1, 0xB681, 0x7640,
0x7200, 0xB2C1, 0xB381, 0x7340, 0xB101, 0x71C0, 0x7080, 0xB041,
0x5000, 0x90C1, 0x9181, 0x5140, 0x9301, 0x53C0, 0x5280, 0x9241,
0x9601, 0x56C0, 0x5780, 0x9741, 0x5500, 0x95C1, 0x9481, 0x5440,
0x9C01, 0x5CC0, 0x5D80, 0x9D41, 0x5F00, 0x9FC1, 0x9E81, 0x5E40,
0x5A00, 0x9AC1, 0x9B81, 0x5B40, 0x9901, 0x59C0, 0x5880, 0x9841,
0x8801, 0x48C0, 0x4980, 0x8941, 0x4B00, 0x8BC1, 0x8A81, 0x4A40,
0x4E00, 0x8EC1, 0x8F81, 0x4F40, 0x8D01, 0x4DC0, 0x4C80, 0x8C41,
0x4400, 0x84C1, 0x8581, 0x4540, 0x8701, 0x47C0, 0x4680, 0x8641,
0x8201, 0x42C0, 0x4380, 0x8341, 0x4100, 0x81C1, 0x8081, 0x4040 )

INITIAL_MODBUS = 0xFFFF
ONE_MINUTE = 60
ONE_DAY = 86400

#function for determining crc bytes
def calcString( st, crc ):
    """Given a binary string and starting CRC, Calc a final CRC-16 """
    for ch in st:
        crc = (crc >> 8) ^ table[(crc ^ ord(ch)) & 0xFF]
    return crc
    
#function exchanges messages with device 
def interface( message ):
    ser.write(message)#send message to serial port. note for different devices a different message will be sent.
    time.sleep(0.5) #wait for response. research a better way to do this?
    return ser.read(ser.inWaiting())
    
#function which takes received hex string and converts to readable format
def dataFormat( raw ):
    hexString = ''.join(i for i in raw[3:7])
    return float( "%.3e" % struct.unpack('<f', hexString)[0])
    
#function which takes a data collection and generates a .csv file
def makeFileAndWipe( data_list ):
    file_name = "%s_%s-to-%s_%s" % (data_list[0][0],data_list[0][1], data_list[-1][0],data_list[-1][1])
    file_name = file_name.replace(':','.')
    save_path = 'C:/Users/LAIR/Desktop/Pressure_Gauge/'
    completeName = os.path.join(save_path, file_name + '.csv')
    with open(completeName, "wb") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(data_list)
        f.close()
    del data_list[:]
    print 'File created!'

#create serial object
ser = serial.Serial(
    'COM38',
    baudrate = 19200, 
    bytesize = 8, 
    timeout = 3, 
    stopbits = serial.STOPBITS_ONE, 
    parity = serial.PARITY_NONE, 
)
#ensure port was opened correctly
if(ser.isOpen() == False):
    ser.open()
    
#initialize twitter bot
CONSUMER_KEY ="rRO814mWSgfKr8K4gt8U3cl4C"
CONSUMER_SECRET = "Sm3vBuNVtEJGar2vYbxNeGeUUs3C6YuB9727MDUD5pagvrX1Hz"   
ACCESS_KEY = "743863271464144896-9ok5kfpIZXwghOjNZFlDdTGORlzcp7k"    
ACCESS_SECRET = "pcFI4M5qSLXuZPdNNqp53ENaJ4VzWB9SZ1FXWEDv62iyS"
auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)

api = tweepy.API(auth)

#create commands to send
message1 = "\x01\x17\x00\x9A\x00\x02\x00\x00\x00\x00\x00"
message2 = "\x02\x17\x00\x9A\x00\x02\x00\x00\x00\x00\x00"

#find corresponding crc
crc1 = calcString(message1, INITIAL_MODBUS)
crc2 = calcString(message2, INITIAL_MODBUS)

#append crc to message
message1 += struct.pack('<H', crc1)
message2 += struct.pack('<H', crc2)

#get desired frequency
timer = int(raw_input("Frequency in seconds: "))

#print starting time
print time.strftime("%Y-%m-%d %H:%M:%S")
print "Please press Ctrl-C to end data collection or alter frequency."

tweet_time = 0
flag = True
start_time = file_time = time.time() #this time is used to control the frequency
data_list = [] #list that will house data, duh
header = ["Date","Time", "Prep (mBar)", "LT (mBar)"] #first line for the CSV file that will be generated


#infinite loop that runs until ctrl-c is pressed. 
while True:
    try:
        if not flag:
            time.sleep(timer - ((time.time() - start_time) % timer)) #frequency control line
            print "\n\n"
        
        #array to hold characters. fix in the future?
        received1 = [] 
        received2 = []
        
        #retrieve data:
        received1 += interface(message1)
        received2 += interface(message2)
        
        #format data
        data1 = dataFormat(received1) if len(received1) > 0 else ''
        data2 = dataFormat(received2) if len(received2) > 0 else ''
            
        #time to be written to file
        write_time = time.strftime("%H:%M:%S") 
        write_date = time.strftime("%Y-%m-%d") 
        
        print 'Date/time: %s, %s.\nPrep Pressure: %s mBar.\nLT Pressure: %s mBar.' % (write_date, write_time, data1, data2)
        print 'Please press Ctrl-C to end data collection or alter frequency.'
        #write time and reading to data list. note list entries are lists themselves.
        data_list.append([write_date, write_time, data1, data2]) 
        #tweet once per minute
        if flag or int(time.time() - tweet_time) >= ONE_MINUTE:
            #exception handling to ensure twitter issues don't crash program
            try:
                api.update_status('Date/time: %s, %s.\nPrep Pressure: %s mBar.\nLT Pressure: %s mBar.' % (write_date, write_time, data1, data2))
                tweet_time = time.time()
            except tweepy.TweepError:
                print '\nError connecting to Twitter. Please check internet connection.\n'
        if flag:
            flag = False
        #if script has run for more than 24 hours
        if int(time.time() - file_time) >= ONE_DAY :
            makeFileAndWipe(data_list)
            file_time = time.time()
        
    
    except KeyboardInterrupt:       #this is the only reasonable way I've found to control infinite loop. 
        command = raw_input("\nTo end enter Q, or enter a number to alter frequency: ")
        if command.lower() == 'q':
            print "Thank you."
            break
        elif command.isdigit():
            timer = int(command)
        else:
            print 'Invalid Entry'

#create .csv upon closing
makeFileAndWipe(data_list)
    

ser.close()
