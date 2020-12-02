import ipfshttpclient
class main():
    '''
    An example plugin for DIY-Hydrus.
    Automatically pins files that get downloaded onto ipfs.
    '''
    universal = None
    files_to_add = {}
    
    global ipfshttpclient

    def delete(self):
        '''
        Had to get added because called plugins dont get deleted b4 DB does.
        I Tried everything :C
        '''
        for each in self.files_to_add:
            self.universal.databaseRef.tag_namespace_manager(str(each), "IPFS")
            self.universal.databaseRef.t_and_f_relation_manager(self.files_to_add[each], str(each))

    def __init__(self, universal):
        '''
        Initial setup of data creates connection to IPFS
        '''
        self.universal = universal
        self.client = self.make_connection()
        #print("init Universal", self.universal)
        #Altering Sqlite3 table to have IPFS storage
        # Code pulled from: https://www.reddit.com/r/learnpython/comments/29zchz/sqlite3_check_if_a_column_exists_if_it_does_not/
        #Deletes the old IPFS table data.
        if "Ipfs" in [i[1] for i in universal.databaseRef.direct_sqlite_return("PRAGMA table_info(File)")]:
            print("Updating IPFS DB to modern standards PLEASEWAIT")
            self.universal.databaseRef.direct_sqlite("""DROP TABLE File_backup""")
            self.universal.databaseRef.direct_sqlite("""CREATE TABLE File_backup(id INTEGER,
                                                hash text, 
                                                filename text,
                                                size real,
                                                ext text)""")
            self.universal.databaseRef.direct_sqlite(""" INSERT INTO File_backup SELECT id,hash,filename,size,ext FROM File """)
            self.universal.databaseRef.direct_sqlite(""" DROP TABLE File """)
            self.universal.databaseRef.direct_sqlite(""" ALTER TABLE File_backup RENAME TO File """)
            self.universal.databaseRef.write()

        universal.databaseRef.namespace_manager("IPFS")
        #Gathering list of empty spots inside of DB.

        namespace_id = universal.databaseRef.pull_data("Namespace", "name", "IPFS")[0][0]
        
        # Backwards compatible to update DB.
        if self.universal.databaseRef.return_count("File", "id") != self.universal.databaseRef.return_count("Tags", "namespace", namespace_id):
            print(self.universal.databaseRef.return_count("File", "id"), self.universal.databaseRef.return_count("Tags", "namespace", namespace_id))
            has_ipfs = self.universal.databaseRef.pull_data("Tags", "namespace", namespace_id)
            
            to_del = []
            for each in has_ipfs:
                try:
                    file_id = self.universal.databaseRef.search_relationships(each[0])
                    to_del.append(file_id[0][1])
                except IndexError:
                    print("ERROR WITH: ", each, file_id)
                    #to_del.append(file_id[0][1])
                    self.universal.databaseRef.delete_data("Tags", "id", each[0])

            for each in to_del:
                try:
                    self.universal.databaseRef.delete_data("Relationship", "tagid", each)
                    self.universal.databaseRef.delete_data("Tags", "id", each)
                except IndexError:
                    print("ERROR WITH A : ", each)
                    self.universal.databaseRef.delete_data("Tags", "id", each[0])

            totallist = self.universal.databaseRef.invert_pull_data("File", "id", "")
            #has_ipfs = []
            file_list = []
            for each in totallist:
                file_id = each[0]
                file_list.append(file_id)
            
            ipfs_list = []
            has_ipfs = self.universal.databaseRef.pull_data("Tags", "namespace", namespace_id)
            for each in has_ipfs:
                try:
                    file_id = self.universal.databaseRef.search_relationships(each[0])[0][0]
                    ipfs_list.append(file_id)
                except IndexError:
                    print(each, file_id)

            parsed_list = set(file_list) - set(ipfs_list)
            print("Parsed List Length", len(parsed_list))
            for each in parsed_list:
                try:
                    self.pin_handler("", totallist[each - 1][2], totallist[each - 1][1])
                except IndexError:
                    print("Err1r with: ", each, totallist[each - 1])

    def make_connection(self):
        '''
        Creates a connection to the IPFS daemon.
        '''
        return ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
    
    def pin_handler(self, *args):
        '''
        Handles the pinning of files to IPFS.
        [1] is the file name
        [2] is the file hash
        '''
        #print("PinHandler")
        if args[0] is None:
            return
        else:
            folder = self.universal.rateLimiter.InternetHandler.check_dir(self, args[2])
            location = folder + args[1]

            result = self.addPin(location)
            universal.log_write.write("DIYHydrus-IPFS-Plugin has pinned: " + str(result["Name"]) + " to the IPFS database. Its hash is: ' " + str(result["Hash"]) + " '")
            print("DIYHydrus-IPFS-Plugin has pinned: " + str(result["Name"]) + " to the IPFS database. Its hash is: ' " + str(result["Hash"]) + " '")
            self.files_to_add[result["Hash"]] = args[2]
            

    def addPin(self, fileLocation):
        '''
        Actually pins files to IPFS
        '''
        return self.client.add(fileLocation, pin = True)

storage = main(universal)

hooks = {"file_download": storage.pin_handler}
