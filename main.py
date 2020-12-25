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

        if self.client is None:
            return


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

        #New updated updating code.
        if self.universal.databaseRef.return_count("File", "id") != self.universal.databaseRef.return_count("Tags", "namespace", namespace_id):
            file = self.universal.databaseRef.pull_data("File", "id", None)
            tag = self.universal.databaseRef.pull_data("Tags", "namespace", namespace_id)

            to_parse = []

            #Loops through tags and file lists and gets results to parse.
            tag_lists = []
            for each in tag:
                relationship = self.universal.databaseRef.search_relationships(each[0])
                tag_lists.append(relationship[0][0])

            file_lists = []
            for each in file:
                file_lists.append(each[0])

            #Error checking for weirdness.
            #Removes all fileids that already have been added by IPFS.
            if len(file_lists) > len(tag_lists):
                to_parse = set(file_lists) - set(tag_lists)

            #Pinning file to IPFS
            for each in to_parse:
                file_data = self.universal.databaseRef.pull_file(each)[0]
                print("IPFS is adding file to share.")
                print(file_data)
                self.pin_handler("main", file_data[2], file_data[1])

    def make_connection(self):
        '''
        Creates a connection to the IPFS daemon.
        '''
        try:
            holder = ipfshttpclient.connect('/ip4/127.0.0.1/tcp/5001')
            return holder
        except ipfshttpclient.exceptions.ConnectionError:
            return None


    def pin_handler(self, *args):
        '''
        Handles the pinning of files to IPFS.
        [1] is the file name
        [2] is the file hash
        '''
        if args[0] is None:
            return
        else:
            folder = self.universal.rateLimiter.InternetHandler.check_dir(self, args[2])
            location = folder + args[1]
            if self.client is None:
                return
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
