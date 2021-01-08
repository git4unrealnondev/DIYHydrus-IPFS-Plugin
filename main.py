from ast import literal_eval as make_tuple
import ipfshttpclient
import base64
import random
import time
import sys
import json

class main():
    '''
    An example plugin for DIY-Hydrus.
    Automatically pins files that get downloaded onto ipfs.
    '''
    universal = None
    files_to_add = {}
    pubsub = True
    counter = 0
    pubsub_name = None
    ipfs_search = 'DIYHydrus-IPFS-Pubsub-Private-v001'

    global ipfshttpclient
    global base64
    global random
    global time
    global sys
    global json
    global make_tuple

    def listener(self, *args):
        print("creating listener")
        print("aaargs", args)
        with self.client.pubsub.subscribe(args[1]) as sub:
            try:
                if args[2]._stop_event.is_set():
                    return
                for message in sub:
                    if args[1] == 'DIYHydrus-IPFS-Pubsub-Introduction' and self.b642str(message["data"]) == str(self.selfhash):
                        self.pubsub_name = message["from"]
                        sys.exit()
                        self.universal.ThreadManager.remove_thread(args[2])

                    if not message["from"] == self.pubsub_name:

                        tup = make_tuple(self.b642str(message["data"]))

                        if not str(tup[0]) in self.universal.databaseRef.pull_data("File", "hash", None):

                            print("Got info on file ", str(tup[2]), " adding to db.")
                            self.universal.log_write.write("DIYHudrus-IPFS-Plugin has added " + str(tup[2]) + " to db. ")

                            data_str = json.dumps(tup[3])
                            data = json.loads(data_str)
                            #print(data)
                            #data["hash"] = str(tup[0])
                            #print(type(data), tup)
                            data["IPFS"] = str(tup[1])
                            temp = []

                            temp.append(str(tup[2]))
                            temp.append(str(tup[0]))

                            data_encapsulate = {}
                            temp_encapsulate = {}
                            data_encapsulate[str(tup[0])] = data
                            temp_encapsulate[str(tup[0])] = temp
                            #print(data_encapsulate, temp_encapsulate)
                            self.universal.scraperHandler.interpret_data(data_encapsulate, temp_encapsulate)


            except Exception as e:
                print(e)
                self.counter += 1
                if self.counter >= 3:
                    sys.exit()
                self.universal.log_write.write("DIYHudrus-IPFS-Plugin ERRORED " + str(e) + str(args))
                self.listener(args[0], args[1], args[2])

    def b642str(self, b64):
        return base64.b64decode(b64).decode('utf-8')

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

        #Checking if IPFS Pubsub is enabled
        self.selfhash = random.getrandbits(256)
        try:
            self.universal.ThreadManager.run_in_thread(self.listener, self, 'DIYHydrus-IPFS-Pubsub-Introduction')
            time.sleep(1)
            print("publishing selfhahs", self.selfhash, self.selfhash)
            self.client.pubsub.publish('DIYHydrus-IPFS-Pubsub-Introduction', self.selfhash)
        except Exception as f:
            print("fail", f)
            self.pubsub = False

        if self.pubsub:
            self.universal.ThreadManager.run_in_thread(self.listener, self, self.ipfs_search)

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
                #print(each, relationship, type(relationship), len(relationship))
                if len(relationship) == 1:
                    tag_lists.append(relationship[0][0])
                else:
                    self.universal.databaseRef.delete_data("Tags", "id", each[0])
                #else:
                #    print(relationship, type(relationship))

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
                #self.pin_handler("main", file_data[2], file_data[1])

    def publish(self, *args):
        '''
        Data should be in this order:
        [0] File Hash
        [1] IPFS Hash
        [2] File Name
        [3] Data
        '''
        self.client.pubsub.publish(self.ipfs_search, str(args))

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
        [3] should be the data for tags.
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

            #Publishes data to IPFS.
            if self.pubsub and len(args) == 4:
                self.publish(args[2], str(result["Hash"]), str(result["Name"]), args[3])


    def addPin(self, fileLocation):
        '''
        Actually pins files to IPFS
        '''
        return self.client.add(fileLocation, pin = True)

storage = main(universal)

hooks = {"file_download": storage.pin_handler}
