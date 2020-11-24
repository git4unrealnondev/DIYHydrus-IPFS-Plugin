import ipfshttpclient
class main():
    '''
    An example plugin for DIY-Hydrus.
    Automatically pins files that get downloaded onto ipfs.
    '''
    global ipfshttpclient

    def __init__(self, universal):
        '''
        Initial setup of data creates connection to IPFS
        '''
        self.universal = universal
        self.client = self.make_connection()
        self.pinLS()

    def make_connection(self):
        '''
        Creates a connection to the IPFS daemon.
        '''
        return ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')

    def pinLS(self):
        '''
        Code to show what is pinned via IPFS.
        NOT BEING USED.
        '''
        aList = self.client.pin.ls()

        json_Obj = aList["Keys"]
        self.pins = []
        for each in json_Obj:
            self.pins.append(each)
            #print(each)
    
    def pin_handler(self, *args):
        '''
        Handles the pinning of files to IPFS.
        '''
        if args[0] is None:
            return
        else:
            result = self.addPin(args[0] + args[1])
            universal.log_write.write("DIYHydrus-IPFS-Plugin has pinned: " + str(result["Name"]) + " to the IPFS database. Its hash is: ' " + str(result["Hash"]) + " '")
            print("DIYHydrus-IPFS-Plugin has pinned: " + str(result["Name"]) + " to the IPFS database. Its hash is: ' " + str(result["Hash"]) + " '")
      
    def addPin(self, fileLocation):
        '''
        Actually pins files to IPFS
        '''
        return self.client.add(fileLocation, pin = True)

storage = main(universal)

hooks = {"file_download": storage.pin_handler, "test1": storage.addPin}
