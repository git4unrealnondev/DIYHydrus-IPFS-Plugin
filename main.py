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

        #Altering Sqlite3 table to have IPFS storage
        # Code pulled from: https://www.reddit.com/r/learnpython/comments/29zchz/sqlite3_check_if_a_column_exists_if_it_does_not/
        #Deletes the old IPFS table data.
        if "Ipfs" in [i[1] for i in universal.databaseRef.direct_sqlite_return("PRAGMA table_info(File)")]:
            universal.databaseRef.direct_sqlite("""DROP TABLE File_backup""")
            universal.databaseRef.direct_sqlite("""CREATE TABLE File_backup(id INTEGER,
                                                hash text, 
                                                filename text,
                                                size real,
                                                ext text)""")
            universal.databaseRef.direct_sqlite(""" INSERT INTO File_backup SELECT id,hash,filename,size,ext FROM File """)
            universal.databaseRef.direct_sqlite(""" DROP TABLE File """)
            universal.databaseRef.direct_sqlite(""" ALTER TABLE File_backup RENAME TO File """)
            universal.databaseRef.write()

        universal.databaseRef.namespace_manager("IPFS")
        #Gathering list of empty spots inside of DB.

        namespace_id = universal.databaseRef.pull_data("Namespace", "name", "IPFS")[0][0]
        
        # Backwards compatible to update DB.
        if universal.databaseRef.return_count("File", "id") != universal.databaseRef.return_count("Tags", "namespace", namespace_id):
            has_ipfs = universal.databaseRef.pull_data("Tags", "namespace", namespace_id)
            
            
            totallist = universal.databaseRef.invert_pull_data("File", "id", "")
            
            file_list = []
            for each in totallist:
                file_id = each[0]
                file_list.append(file_id)
            
            ipfs_list = []
            for each in has_ipfs:
                file_id = universal.databaseRef.search_relationships(each[0])[0][0]
                ipfs_list.append(file_id)
            
            parsed_list = set(file_list) - set(ipfs_list)
            
            for each in parsed_list:
                self.pin_handler("", totallist[each][1], totallist[each][2])

    def make_connection(self):
        '''
        Creates a connection to the IPFS daemon.
        '''
        return ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
    
    def pin_handler(self, *args):
        '''
        Handles the pinning of files to IPFS.
        [1] is the file hash
        [2] is the file name
        '''
        if args[0] is None:
            return
        else:

            folder = self.universal.rateLimiter.InternetHandler.check_dir(self, args[1])
            location = folder + args[2]

            result = self.addPin(location)
            universal.log_write.write("DIYHydrus-IPFS-Plugin has pinned: " + str(result["Name"]) + " to the IPFS database. Its hash is: ' " + str(result["Hash"]) + " '")
            print("DIYHydrus-IPFS-Plugin has pinned: " + str(result["Name"]) + " to the IPFS database. Its hash is: ' " + str(result["Hash"]) + " '")
            universal.databaseRef.tag_namespace_manager(str(result["Hash"]), "IPFS")
            universal.databaseRef.t_and_f_relation_manager(args[1], str(result["Hash"]))

    def addPin(self, fileLocation):
        '''
        Actually pins files to IPFS
        '''
        return self.client.add(fileLocation, pin = True)

storage = main(universal)

hooks = {"database_writing": storage.pin_handler, "test1": storage.addPin}
